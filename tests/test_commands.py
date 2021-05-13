from chat import commands


class MockContext(commands.CommandContext):
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
        pass


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


def test_unknown_command():
    context = MockContext(
        message="u3 Hey there", current_username="u1", all_usernames=["u1", "u2", "u3"]
    )
    commands.handle_command("bar", context)
    assert context.messages_sent["u1"] == ["Unknown command: bar"]
