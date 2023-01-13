from babel.messages.frontend import CommandLineInterface


def build(src: str, dst: str):
    CommandLineInterface().run(
        [
            "pybabel",
            "compile",
            "-D",
            "nb-cli-plugin-rplugin",
            "-d",
            "nb_cli_plugin_rplugin/locale/",
        ]
    )


if __name__ == "__main__":
    build("", "")
