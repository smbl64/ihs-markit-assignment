from chat import commands, helpers


class MockContext(commands.CommandContext):
    """
    A command context which simulates the real server's actions.
    """
    def __init__(self, *, message, current_username, all_usernames):
        self.message = message
        self.current_username = current_username
        self.all_usernames = all_usernames

        self.messages_sent = dict()

    def get_message(self):
        return self.message

    def get_all_usernames(self):
        return self.all_usernames

    def get_current_username(self):
        return self.current_username

    def send_message(self, message: str) -> bool:
        self.messages_sent.setdefault(self.current_username, []).append(message)
        return True

    def send_message_to_other_user(
        self, receipient: str, message: str, *, sender: str = None
    ) -> bool:
        if receipient not in self.all_usernames:
            return False

        self.messages_sent.setdefault(receipient, []).append(message)
        return True

    def is_user_online(self, username: str) -> bool:
        return username in self.all_usernames

    def run_in_background(
        self, *, job_func, job_func_kwargs, callback_func, callback_func_kwargs
    ) -> None:
        if not job_func_kwargs:
            job_func_kwargs = dict()

        if not callback_func_kwargs:
            callback_func_kwargs = dict()

        ret_value = job_func(**job_func_kwargs)
        callback_func(ret_value, **callback_func_kwargs)


def test_unknown_command():
    context = MockContext(
        message="u3 Hey there", current_username="u1", all_usernames=["u1", "u2", "u3"]
    )
    commands.handle_command("bar", context)
    assert context.messages_sent["u1"] == ["Unknown command: bar"]


def test_whois_command():
    context = MockContext(message="", current_username="u1", all_usernames=["u1"])
    commands.whois_command(context)
    assert context.messages_sent["u1"] == ["No other user is connected."]

    context = MockContext(message="", current_username="u1", all_usernames=["u1", "u2"])
    commands.whois_command(context)
    assert context.messages_sent["u1"] == ["Online users: u2"]


def test_broadcast_command():
    context = MockContext(
        message="Hey there", current_username="u1", all_usernames=["u1", "u2"]
    )
    commands.broadcast_command(context)
    assert "u1" not in context.messages_sent
    assert context.messages_sent["u2"] == ["Hey there"]


def test_msg_command():
    context = MockContext(
        message="u3 Hey there", current_username="u1", all_usernames=["u1", "u2", "u3"]
    )
    commands.msg_command(context)
    assert "u2" not in context.messages_sent
    assert context.messages_sent["u1"] == ["Message is delivered to u3"]
    assert context.messages_sent["u3"] == ["Hey there"]


def test_url_command(monkeypatch):
    context = MockContext(
        message="u2 https://www.google.com",
        current_username="u1",
        all_usernames=["u1", "u2"],
    )

    def mockreturn(*args, **kwargs):
        return 123

    monkeypatch.setattr(helpers, "get_remote_resource_length", mockreturn)
    commands.url_command(context)
    assert context.messages_sent["u1"] == ["URL size is delivered to u2"]
    assert context.messages_sent["u2"] == ["resource_size(https://www.google.com) = 123"]


def test_fib_command():
    context = MockContext(
        message="u2 5", current_username="u1", all_usernames=["u1", "u2"]
    )
    commands.fib_command(context)
    assert context.messages_sent["u1"] == ["Fib result is delivered to u2"]
    assert context.messages_sent["u2"] == ["fib(5) = 5"]
