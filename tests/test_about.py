def test_version():
    from dough.__about__ import __version__

    assert isinstance(__version__, str)
