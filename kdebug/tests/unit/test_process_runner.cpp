#include "core/process/process_runner.h"

#include <cassert>
#include <cerrno>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <string>
#include <signal.h>
#include <sys/wait.h>
#include <unistd.h>

int main() {
    kdebug::ProcessRunner runner;

    {
        kdebug::ProcessRequest request;
        request.executable = "/bin/sh";
        request.argv = {"-c", "cat; printf 'stderr-ok\\n' >&2"};
        request.stdin_text = "stdin-ok\n";
        request.timeout_ms = 2000;
        kdebug::ProcessResult result = runner.run(request);
        assert(result.exit_code == 0);
        assert(!result.timed_out);
        assert(result.stdout_text == "stdin-ok\n");
        assert(result.stderr_text == "stderr-ok\n");
    }

    {
        kdebug::ProcessRequest request;
        request.executable = "/bin/sh";
        request.argv = {
            "-c",
            "i=0; while [ $i -lt 12000 ]; do printf 'stdout-%05d\\n' $i; "
            "printf 'stderr-%05d\\n' $i >&2; i=$((i+1)); done"
        };
        request.timeout_ms = 5000;
        kdebug::ProcessResult result = runner.run(request);
        assert(result.exit_code == 0);
        assert(result.stdout_text.find("stdout-11999") != std::string::npos);
        assert(result.stderr_text.find("stderr-11999") != std::string::npos);
    }

    {
        kdebug::ProcessRequest request;
        request.executable = "/bin/sh";
        request.argv = {"-c", "sleep 5"};
        request.timeout_ms = 100;
        const auto begin = std::chrono::steady_clock::now();
        kdebug::ProcessResult result = runner.run(request);
        const long long elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - begin).count();
        assert(result.timed_out);
        assert(result.exit_code == -1);
        assert(elapsed_ms < 2000);
    }

    {
        kdebug::ProcessRequest request;
        request.executable = "/path/that/does/not/exist";
        request.timeout_ms = 1000;
        kdebug::ProcessResult result = runner.run(request);
        assert(result.exit_code == 127);
        assert(result.stderr_text.find("failed to exec") != std::string::npos);
    }

    {
        const std::string marker =
            "/tmp/kdebug-process-runner-descendant-" + std::to_string(getpid());
        std::remove(marker.c_str());
        kdebug::ProcessRequest request;
        request.executable = "/bin/sh";
        request.argv = {
            "-c",
            "(trap '' TERM; sleep 1; printf leaked > '" + marker +
                "') & trap 'exit 0' TERM; wait"
        };
        request.timeout_ms = 100;
        kdebug::ProcessResult result = runner.run(request);
        assert(result.timed_out);
        usleep(1200000);
        assert(access(marker.c_str(), F_OK) != 0);
        std::remove(marker.c_str());
    }

    {
        const std::string pid_path =
            "/tmp/kdebug-process-runner-pdeath-" + std::to_string(getpid());
        std::remove(pid_path.c_str());
        const pid_t middle = fork();
        assert(middle >= 0);
        if (middle == 0) {
            kdebug::ProcessRequest request;
            request.executable = "/bin/sh";
            request.argv = {
                "-c",
                "echo $$ > '" + pid_path +
                    "'; trap 'exit 0' TERM; while :; do :; done"
            };
            request.timeout_ms = 5000;
            runner.run(request);
            _exit(0);
        }

        pid_t child = -1;
        for (int i = 0; i < 200 && child <= 0; ++i) {
            std::ifstream stream(pid_path.c_str());
            if (stream.good()) stream >> child;
            if (child <= 0) usleep(10000);
        }
        assert(child > 1);
        kill(middle, SIGKILL);
        int middle_status = 0;
        while (waitpid(middle, &middle_status, 0) < 0 && errno == EINTR) {}

        bool child_gone = false;
        for (int i = 0; i < 200; ++i) {
            if (kill(child, 0) != 0 && errno == ESRCH) {
                child_gone = true;
                break;
            }
            usleep(10000);
        }
        if (!child_gone) kill(-child, SIGKILL);
        std::remove(pid_path.c_str());
        assert(child_gone);
    }

    return 0;
}
