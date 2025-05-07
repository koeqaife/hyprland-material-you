#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#define BUFFER_SIZE 1024

int main(int argc, char *argv[]) {
    int sockfd;
    struct sockaddr_un addr;
    char buffer[BUFFER_SIZE];

    const char *instance = getenv("HYPRLAND_INSTANCE_SIGNATURE");
    if (!instance) {
        fprintf(stderr, "HYPRLAND_INSTANCE_SIGNATURE is not set.\n");
        return 1;
    }

    char socket_path[BUFFER_SIZE];
    snprintf(socket_path, sizeof(socket_path), "/tmp/hypryou/sockets/%s", instance);

    if (argc < 2) {
        fprintf(stderr, "Usage: %s <command> [args...]\n", argv[0]);
        return 1;
    }

    char command[BUFFER_SIZE] = {0};
    for (int i = 1; i < argc; ++i) {
        strncat(command, argv[i], BUFFER_SIZE - strlen(command) - 1);
        if (i < argc - 1) {
            strncat(command, " ", BUFFER_SIZE - strlen(command) - 1);
        }
    }

    sockfd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (sockfd == -1) {
        perror("socket");
        return 1;
    }

    memset(&addr, 0, sizeof(struct sockaddr_un));
    addr.sun_family = AF_UNIX;
    strlcpy(addr.sun_path, socket_path, sizeof(addr.sun_path));

    if (connect(sockfd, (struct sockaddr *)&addr, sizeof(struct sockaddr_un)) == -1) {
        perror("connect");
        fprintf(stderr, "Failed to connect to socket: %s\n", socket_path);
        close(sockfd);
        return 1;
    }

    if (write(sockfd, command, strlen(command)) == -1) {
        perror("write");
        close(sockfd);
        return 1;
    }

    ssize_t num_read = read(sockfd, buffer, BUFFER_SIZE - 1);
    if (num_read > 0) {
        buffer[num_read] = '\0';
        printf("%s\n", buffer);
    } else {
        perror("read");
    }

    close(sockfd);
    return 0;
}
