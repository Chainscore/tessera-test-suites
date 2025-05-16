from jam.consensus.safrole.safrole import Safrole


def test_safrole():
    safrole = Safrole()
    assert safrole.__class__.__name__ == "Safrole"
