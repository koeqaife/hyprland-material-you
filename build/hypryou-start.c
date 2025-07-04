#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <errno.h>
#include <pwd.h>
#include <sys/stat.h>
#include <sys/types.h>

#define MAX_RETRIES 5
#define RETRY_TIMEOUT 10
#define WORKING_DIR "/opt/hypryou"

static int mkdir_p(const char *path, mode_t mode)
{
    char tmp[512];
    char *p = NULL;
    size_t len;
    snprintf(tmp, sizeof(tmp), "%s", path);
    len = strlen(tmp);
    if (tmp[len - 1] == '/')
        tmp[len - 1] = '\0';
    for (p = tmp + 1; *p; p++)
    {
        if (*p == '/')
        {
            *p = '\0';
            if (mkdir(tmp, mode) != 0 && errno != EEXIST)
                return -1;
            *p = '/';
        }
    }
    if (mkdir(tmp, mode) != 0 && errno != EEXIST)
        return -1;
    return 0;
}

static void show_crash_dialog(int exit_code)
{
    char exit_code_str[16];
    snprintf(exit_code_str, sizeof(exit_code_str), "--code=%d", exit_code);
    execlp("hypryou-crash-dialog", "hypryou-crash-dialog", exit_code_str, NULL);
    perror("Failed to launch crash dialog");
}

static void strip_ansi_and_write(FILE *fout, const char *buf, ssize_t len)
{
    ssize_t i = 0;
    while (i < len)
    {
        if (buf[i] == '\x1b')
        {
            i++;
            if (i < len && buf[i] == '[')
            {
                i++;
                while (i < len && ((buf[i] < '@') || (buf[i] > '~')))
                    i++;
                if (i < len)
                    i++;
            }
        }
        else
        {
            fputc(buf[i++], fout);
        }
    }
}

int main(void)
{
    if (chdir(WORKING_DIR) != 0)
    {
        fprintf(stderr, "Failed to chdir to %s: %s\n", WORKING_DIR, strerror(errno));
        show_crash_dialog(-2);
        return 1;
    }

    int retry_count = 0;
    time_t start_time = time(NULL);

    while (1)
    {
        time_t current_time = time(NULL);
        if ((current_time - start_time) > RETRY_TIMEOUT)
            retry_count = 0;
        start_time = current_time;

        const char *home_dir = getenv("HOME");
        if (!home_dir)
        {
            struct passwd *pw = getpwuid(getuid());
            home_dir = pw->pw_dir;
        }

        char crash_dir[512];
        snprintf(crash_dir, sizeof(crash_dir), "%s/.cache/hypryou/crashes", home_dir);
        if (mkdir_p(crash_dir, 0755) != 0)
            fprintf(stderr, "Failed to create crash log directory: %s\n", strerror(errno));

        time_t now = time(NULL);
        struct tm *tm_info = localtime(&now);
        char timestamp[64];
        strftime(timestamp, sizeof(timestamp),
                 "crashLog-%Y-%m-%d_%H-%M-%S.txt", tm_info);

        char log_path[512];
        snprintf(log_path, sizeof(log_path), "%s/%s", crash_dir, timestamp);

        int pipefd[2];
        if (pipe(pipefd) == -1)
        {
            perror("pipe failed");
            return 1;
        }

        pid_t pid = fork();
        if (pid == 0)
        {
            close(pipefd[0]);
            dup2(pipefd[1], STDOUT_FILENO);
            dup2(pipefd[1], STDERR_FILENO);
            close(pipefd[1]);
            execlp("python", "python", "-OO", "hypryou_ui.py", NULL);
            perror("exec failed");
            exit(127);
        }

        close(pipefd[1]);

        size_t buf_capacity = 65536;
        size_t buf_size = 0;
        char *output_buf = malloc(buf_capacity);
        if (!output_buf)
        {
            perror("malloc failed");
            close(pipefd[0]);
            return 1;
        }

        char temp_buf[4096];
        ssize_t nread;
        while ((nread = read(pipefd[0], temp_buf, sizeof(temp_buf))) > 0)
        {
            ssize_t n = nread;

            if (write(STDOUT_FILENO, temp_buf, (size_t)n) == -1)
            {
                perror("write failed");
                break;
            }

            if (buf_size + (size_t)n > buf_capacity)
            {
                buf_capacity *= 2;
                char *new_buf = realloc(output_buf, buf_capacity);
                if (!new_buf)
                {
                    free(output_buf);
                    perror("realloc failed");
                    close(pipefd[0]);
                    return 1;
                }
                output_buf = new_buf;
            }

            memcpy(output_buf + buf_size, temp_buf, (size_t)n);
            buf_size += (size_t)n;
        }
        close(pipefd[0]);

        int status;
        waitpid(pid, &status, 0);

        if (WIFEXITED(status))
        {
            int code = WEXITSTATUS(status);

            if (code == 0 || code == 100)
            {
                free(output_buf);
                if (code == 100)
                    printf("App asked for reload (exit code: %d)\n", code);
                else
                    printf("App exited normally.\n");
                continue;
            }

            FILE *log_file = fopen(log_path, "w");
            if (log_file)
            {
                strip_ansi_and_write(log_file, output_buf, (ssize_t)buf_size);
                fclose(log_file);
                fprintf(stderr, "Crash log saved to %s\n", log_path);
            }
            else
            {
                perror("Failed to save crash log");
            }

            free(output_buf);

            retry_count++;
            if (retry_count >= MAX_RETRIES)
            {
                fprintf(stderr, "App failed too many times.\n");
                show_crash_dialog(code);
                return 1;
            }

            printf("App exited with %d, retrying (%d/%d)...\n",
                   code, retry_count, MAX_RETRIES);
            sleep(1);
        }
        else
        {
            fprintf(stderr, "App crashed abnormally.\n");

            FILE *log_file = fopen(log_path, "w");
            if (log_file)
            {
                strip_ansi_and_write(log_file, output_buf, (ssize_t)buf_size);
                fclose(log_file);
                fprintf(stderr, "Crash log saved to %s\n", log_path);
            }
            else
            {
                perror("Failed to save crash log");
            }

            free(output_buf);

            show_crash_dialog(-1);
            retry_count++;
            sleep(1);
        }
    }

    return 0;
}
