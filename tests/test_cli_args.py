from deckgen.cli import build_arg_parser


def test_arg_parser_defaults_and_overrides():
    p = build_arg_parser()
    ns = p.parse_args(["--topic", "Flags", "--size", "60", "--format", "anki", "--format", "csv"])
    assert ns.topic == "Flags"
    assert ns.size == 60
    assert ns.format == ["anki", "csv"]
    assert ns.regen == 1
    assert ns.concurrency == 10
    assert not ns.overwrite
