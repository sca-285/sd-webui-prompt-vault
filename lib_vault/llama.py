"""llama-server processes: started when needed, kept warm, stopped when idle.

One process per model (Qwen, TIPO), each on its own 127.0.0.1 port. Nothing
leaves the machine. With "Run one model at a time" on (the default), starting
one stops the other, so they never sit in VRAM together.

Why a server rather than a library in the WebUI's own Python: the model loads
once and then answers in a second or two, a crash cannot take the WebUI down,
and llama-server builds exist for every GPU without compiling anything.
"""

from __future__ import annotations

import atexit
import os
import socket
import subprocess
import threading
import time

from . import TAG, settings

_all: list["LlamaServer"] = []
# one lock for all of them: starting one stops the others, and two locks could deadlock
_lock = threading.RLock()


def _free_port(preferred):
    """The preferred port when it is free, otherwise the next one that is."""
    for candidate in range(int(preferred), int(preferred) + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", candidate))
                return candidate
            except OSError:
                continue
    return int(preferred)


def _healthy(url, timeout=2.0):
    import requests

    try:
        response = requests.get(f"{url}/health", timeout=timeout)
    except Exception:
        return False
    if response.status_code != 200:
        return False
    try:
        return response.json().get("status") in (None, "ok")
    except Exception:
        return True


class LlamaServer:
    def __init__(self, name, port_opt, idle_opt, model_args, missing, extra_opt, layers_opt):
        self.name = name
        self.port_opt, self.idle_opt, self.extra_opt, self.layers_opt = port_opt, idle_opt, extra_opt, layers_opt
        self.model_args = model_args  # -> ["-m", path, ...]; may download first
        self.missing = missing  # -> list of what is not set up, [] when ready
        self.lock = _lock
        self.proc: subprocess.Popen | None = None
        self.url: str | None = None
        self.model: str | None = None
        self.last_used = 0.0
        self.reaper: threading.Thread | None = None
        self.log: list[str] = []
        _all.append(self)

    def say(self, message):
        print(f"{TAG} {self.name}: {message}")

    # -------------------------------------------------------------- process

    def _argv(self, port, model_args):
        server = settings.clean_path(settings.opt("pv_llama_server_path"))
        argv = [server, *model_args, "--host", "127.0.0.1", "--port", str(port),
                "-ngl", str(int(settings.opt(self.layers_opt)))]
        argv += str(settings.opt(self.extra_opt) or "").split()
        return argv

    def _pump(self, stream):
        """Drain the output so the pipe cannot fill up and block the server; keep the
        last lines to explain a failed start."""
        for raw in iter(stream.readline, ""):
            line = raw.rstrip()
            if not line:
                continue
            self.log.append(line)
            del self.log[:-40]
            if bool(settings.opt("pv_vlm_verbose")):
                print(f"{TAG} [{self.name} server] {line}")
        try:
            stream.close()
        except Exception:
            pass

    def _reap_loop(self):
        while True:
            time.sleep(15)
            with self.lock:
                if self.proc is None:
                    self.reaper = None
                    return
                minutes = int(settings.opt(self.idle_opt))
                if minutes > 0 and time.time() - self.last_used > minutes * 60:
                    self.say(f"idle for {minutes} min, stopping it to free its memory")
                    self._stop_locked()
                    self.reaper = None
                    return

    # -------------------------------------------------------------- leftovers

    def _pid_file(self):
        return os.path.join(settings.data_dir(), f".llama-{self.name.lower()}.pid")

    def _reap_leftover(self):
        """A server this extension started before the WebUI crashed or was killed keeps
        running, with its model in VRAM. Its PID was written down: stop it."""
        path = self._pid_file()
        try:
            with open(path, encoding="utf-8") as f:
                pid = int(f.read().split()[0])
        except Exception:
            return
        try:
            import psutil

            proc = psutil.Process(pid)
            cmdline = " ".join(proc.cmdline())
            if "--port" in cmdline and "llama" in cmdline.lower():
                self.say(f"stopping a server left over from an earlier session (pid {pid})")
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except Exception:
                    proc.kill()
        except Exception:
            pass
        try:
            os.remove(path)
        except Exception:
            pass

    def _start_locked(self):
        self._reap_leftover()
        problems = self.missing()
        if problems:
            raise RuntimeError("not set up yet: " + "; ".join(problems))
        if bool(settings.opt("pv_llm_one_at_a_time")):
            for other in _all:
                if other is not self:
                    other.stop()

        model_args = self.model_args()
        port = _free_port(settings.opt(self.port_opt))
        argv = self._argv(port, model_args)
        self.say(f"starting llama-server on 127.0.0.1:{port}")

        creation = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        self.log.clear()
        proc = subprocess.Popen(
            argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", cwd=os.path.dirname(argv[0]) or None, creationflags=creation,
        )
        threading.Thread(target=self._pump, args=(proc.stdout,), daemon=True).start()

        url = f"http://127.0.0.1:{port}"
        deadline = time.time() + int(settings.opt("pv_vlm_startup_timeout"))
        while time.time() < deadline:
            if proc.poll() is not None:
                tail = "\n".join(self.log[-12:])
                raise RuntimeError(f"llama-server exited with code {proc.returncode} before it was ready.\n{tail}")
            if _healthy(url):
                break
            time.sleep(0.5)
        else:
            _terminate(proc)
            raise RuntimeError("llama-server did not become ready in time. Raise the startup timeout, "
                               "or turn on the verbose setting to see its log.")

        self.proc, self.url, self.last_used = proc, url, time.time()
        try:
            with open(self._pid_file(), "w", encoding="utf-8") as f:
                f.write(str(proc.pid))
        except Exception:
            pass
        self.model = next((model_args[i + 1] for i, a in enumerate(model_args[:-1]) if a == "-m"), None)
        self.say(f"ready at {url}")
        if self.reaper is None or not self.reaper.is_alive():
            self.reaper = threading.Thread(target=self._reap_loop, daemon=True)
            self.reaper.start()
        return url

    def ensure(self):
        """The base URL of a live server, starting one when needed."""
        with self.lock:
            if self.proc is not None and self.proc.poll() is None and self.url and _healthy(self.url):
                self.last_used = time.time()
                return self.url
            if self.proc is not None:
                self.say("the server went away, starting it again")
                self._stop_locked()
            return self._start_locked()

    def running(self):
        with self.lock:
            return self.proc is not None and self.proc.poll() is None

    def touch(self):
        with self.lock:
            self.last_used = time.time()

    def _stop_locked(self):
        proc, self.proc, self.url, self.model = self.proc, None, None, None
        if proc is not None and proc.poll() is None:
            _terminate(proc)
        if proc is not None:
            try:
                os.remove(self._pid_file())
            except Exception:
                pass

    def stop(self):
        with self.lock:
            running = self.proc is not None and self.proc.poll() is None
            self._stop_locked()
        if running:
            self.say("stopped")
        return running

    def restart_if_model_changed(self, wanted):
        """A different model was chosen in Settings: the running server has the old one."""
        with self.lock:
            if self.proc is not None and self.model and wanted and \
                    os.path.normcase(os.path.abspath(self.model)) != os.path.normcase(os.path.abspath(wanted)):
                self.say("the model was changed in Settings, restarting")
                self._stop_locked()

    def status(self):
        with self.lock:
            if self.proc is None or self.proc.poll() is not None:
                problems = self.missing()
                return f"{self.name}: " + ("not set up: " + "; ".join(problems) if problems else "stopped")
            return f"{self.name}: running at {self.url}, idle {int(time.time() - self.last_used)}s"

    # -------------------------------------------------------------- requests

    def post(self, path, body, timeout=300):
        import requests

        url = self.ensure()
        try:
            response = requests.post(f"{url}{path}", json=body, timeout=timeout)
        except Exception as exc:
            raise RuntimeError(f"could not reach the {self.name} server: {exc}") from None
        if response.status_code != 200:
            raise RuntimeError(f"the {self.name} server answered {response.status_code}: {response.text[:400]}")
        self.touch()
        try:
            return response.json()
        except Exception:
            raise RuntimeError(f"unexpected answer from the {self.name} server: {response.text[:400]}") from None


def _terminate(proc):
    try:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    except Exception as exc:
        print(f"{TAG} could not stop a llama-server cleanly: {exc}")


def server_missing():
    server = settings.clean_path(settings.opt("pv_llama_server_path"))
    if not server:
        return ["the llama-server executable is not set (Settings > Prompt Vault (Qwen / llama-server))"]
    if not os.path.isfile(server):
        return [f"llama-server not found: {server}"]
    return []


def reap_leftovers():
    """At start-up: servers a crashed or killed WebUI left running."""
    for s in list(_all):
        with s.lock:
            if s.proc is None:
                s._reap_leftover()


def stop_all():
    return [s.name for s in list(_all) if s.stop()]


def status_all():
    return "\n".join(s.status() for s in _all)


atexit.register(stop_all)
try:  # Reload UI / shutdown from the WebUI
    from modules import script_callbacks

    script_callbacks.on_before_reload(stop_all)
except Exception:
    pass
