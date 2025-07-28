# Starman for Python

![Python CI](https://github.com/your-repo/starman-python/actions/workflows/python-ci.yml/badge.svg)

**Starman** is a high-performance preforking WSGI web server for Python. It is a port of the original [Perl Starman](https://github.com/miyagawa/Starman) server, designed to be robust, fast, and feature-rich for production environments on UNIX-like systems.

## Overview and Purpose

Starman brings the battle-tested process management model of preforking servers to the Python WSGI ecosystem. The primary goal is to provide a simple yet powerful standalone server for running Python web applications, with a focus on performance, stability, and efficient resource utilization through copy-on-write memory savings.

It is ideal for developers and system administrators who need a reliable WSGI server that can be managed with standard UNIX signals and integrated with process supervisors like `systemd`, `supervisord`, or `circus`.

## Features

-   **High Performance**: Uses the fast `httptools` library for HTTP parsing and a lean, compiled core loop.
-   **Preforking Architecture**: A master process manages a pool of worker processes, providing isolation and stability. Dead workers are automatically reaped and replaced.
-   **UNIX Signal Management**:
    -   `HUP`: Graceful worker restart (finish serving existing requests, then reload).
    -   `TTIN`/`TTOU`: Increase or decrease the number of worker processes on the fly.
    -   `QUIT`: Graceful shutdown of the entire server.
    -   `INT`/`TERM`: Immediate shutdown.
-   **Hot Deploys**: Superdaemon-aware, supporting process managers like `server_starter` for zero-downtime application upgrades.
-   **Multiple Listeners**: Can bind to multiple TCP ports and UNIX domain sockets simultaneously.
-   **Memory Efficiency**: The `--preload-app` option loads the application in the master process before forking, allowing workers to share memory pages (Copy-on-Write).
-   **WSGI Compliant**: Runs any WSGI-compliant application or framework (e.g., Flask, Django, Falcon).
-   **HTTP/1.1 Support**: Features keep-alive connections, chunked encoding for requests and responses, and request pipelining.
-   **WSGI Extensions**: Includes `wsgix.informational` for sending 1xx informational responses like 103 Early Hints.
-   **UNIX Only**: Designed specifically for and tested on UNIX-like operating systems. It does not support Windows.

## Architecture Summary

Starman operates with a single master process and multiple worker processes.

1.  **Master Process**:
    -   Binds to the specified TCP ports or UNIX sockets.
    -   (Optionally) preloads the WSGI application.
    -   Forks a configurable number of worker processes.
    -   Manages the worker pool: restarts workers that die, and handles signals to adjust the pool size or perform restarts/shutdowns.
    -   Does not handle any client connections itself.

2.  **Worker Processes**:
    -   If the app is not preloaded, each worker loads the WSGI application upon starting.
    -   All workers enter a loop, accepting new connections from the shared listener sockets.
    -   Each worker processes multiple requests on a connection if keep-alive is enabled.
    -   The `httptools` library is used for efficient parsing of incoming HTTP requests.

This model provides robustness, as a crash in one worker does not affect the master or other workers. It also allows for efficient scaling on multi-core systems.

## Setup and Installation

### Prerequisites

-   Python 3.8 or newer
-   A UNIX-like operating system (Linux, macOS, BSD)
-   A C compiler to build the `httptools` dependency.

### Installation

You can install Starman from PyPI using pip:

