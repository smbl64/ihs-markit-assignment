# IHS Markit assignment

This is a simple chat server written in Python. You can use `telnet`, `nc` or any other tool to connect to the server and communicate with it.

## Using the server

### Production

The chat server has no external dependency. Simply clone the repository and then run

```
python -m chat
```

Server will run on `localhost:1235`.

**Note:** If you are on macOS, set the following environment variable before running the server, otherwise the `url` command will not work.

```
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
```
Details on StackOverflow: https://stackoverflow.com/a/52230415/671988




### Running the tests

First, install the dependencies

```
pip install -r requirements.txt
```

Then you can run `pytest` to see the test results.

## Design

There are 3 main modules in the project:

- `server.py`
- `worker.py`
- `commands.py`

### server.py

Application's main loop is in this module. For each new connection, an instance of `ClientHandler` is created which has its own loop for receiving and processing a client's commands.

Another class worth mentioning is the `HandlerRegistry`. This class keeps track of online users and their respective `ClientHandler`.

### worker.py

Since certain commands (e.g. `fib` command) can take some time to finish. For these, I decided to create a job processing mechanism that run a job in the background and return the results.

I have used the `multiprocessing` module to spawn a fixed number of "worker" processes. These processes wait for a "job" to show up in their job queue, then they will process the job and put the result in their result queue.

The class `JobManager` manages these workers, queues the jobs received from client handlers, and then calls the callbacks specified for each job. 

It also has its own thread that runs in the main process' context and monitors the results' queue. If something shows up in the queue, it will call the callback passing the received result.

Another class worth mentioning is `JobWorker`. This class is a wrapper around the `multiprocessing.Process`.

### commands.py

All commands (`w`, `fib` etc) are defined in this module. Each of them is marked with the `@command` decorator.

A command needs an instance of `CommandContext` to do its job. The context will provide some details (such as current username) and certain functionality (e.g. "send a message to anther user"). 

When a client handler needs to run a command, it will invoke `commands.handle_command` and `handle_command` routes the request to the proper command function.

## Further improvements

As with any other project, there is room for improvement. Below I have listed some areas that can be improved:

1. There is no mechanism to prevent the workers from crashing and also re-creating workers if they did crash.
2. Code quality can be improved further by adding more type hints.
3. Right now test cases only cover the "happy path" and there is no test case for edge cases (such as passing invalid parameters to a server command).
4. Configurations (IP, port, number of workers etc) are hardcoded. They should be configurable via environment variables and/or a config file.
5. Tests can be expanded using integration tests. It's possible to spawn a real server (on an actual port) and send real commands to it.
6. Right now each new user gets a new thread. A better approach would be to have a thread-pool and limit the number of accepted connections.

