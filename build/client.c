#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#define BUFFER_SIZE 1024

int main(int argc, char *argv[])
{
    int sockfd;
    struct sockaddr_un addr;
    char buffer[BUFFER_SIZE];

    const char *instance = getenv("HYPRLAND_INSTANCE_SIGNATURE");
    if (!instance)
    {
        fprintf(stderr, "HYPRLAND_INSTANCE_SIGNATURE is not set.\n");
        return 1;
    }

    const char *base_dir = getenv("HYPRYOU_SOCKET_DIR");
    if (!base_dir)
    {
        base_dir = "/tmp/hypryou/sockets";
    }

    char socket_path[BUFFER_SIZE];
    if (snprintf(socket_path, sizeof(socket_path), "%s/%s", base_dir, instance) >= (int)sizeof(socket_path))
    {
        fprintf(stderr, "Socket path too long.\n");
        return 1;
    }

    if (argc < 2)
    {
        fprintf(stderr, "Usage: %s <command> [args...]\n", argv[0]);
        return 1;
    }

    char command[BUFFER_SIZE] = {0};
    int arg_start = 1;
    if (argc > 1 && strcmp(argv[1], "--") == 0)
    {
        arg_start = 2;
    }

    for (int i = arg_start; i < argc; ++i)
    {
        if (strlen(command) + strlen(argv[i]) + 1 >= BUFFER_SIZE)
        {
            fprintf(stderr, "Command too long.\n");
            return 1;
        }
        strncat(command, argv[i], BUFFER_SIZE - strlen(command) - 1);
        if (i < argc - 1)
        {
            strncat(command, " ", BUFFER_SIZE - strlen(command) - 1);
        }
    }

    sockfd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (sockfd == -1)
    {
        perror("socket");
        return 1;
    }

    memset(&addr, 0, sizeof(struct sockaddr_un));
    addr.sun_family = AF_UNIX;

    if (strlen(socket_path) >= sizeof(addr.sun_path))
    {
        fprintf(stderr, "Socket path too long for sockaddr_un.\n");
        close(sockfd);
        return 1;
    }

    strncpy(addr.sun_path, socket_path, sizeof(addr.sun_path) - 1);
    addr.sun_path[sizeof(addr.sun_path) - 1] = '\0';

    if (connect(sockfd, (struct sockaddr *)&addr, sizeof(struct sockaddr_un)) == -1)
    {
        perror("connect");
        fprintf(stderr, "Failed to connect to socket: %s\n", socket_path);
        close(sockfd);
        return 1;
    }

    if (send(sockfd, command, strlen(command), 0) == -1)
    {
        perror("send");
        close(sockfd);
        return 1;
    }

    ssize_t num_read;
    while ((num_read = read(sockfd, buffer, BUFFER_SIZE - 1)) > 0)
    {
        buffer[num_read] = '\0';
        fputs(buffer, stdout);
    }
    if (num_read < 0)
    {
        perror("read");
    }
    if (num_read >= 0 && (num_read == 0 || buffer[num_read - 1] != '\n'))
    {
        putchar('\n');
    }

    close(sockfd);
    return 0;
}
