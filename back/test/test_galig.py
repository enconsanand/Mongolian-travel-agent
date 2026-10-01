from app.utils.galig import latin_to_cyrillic


def test_informal_galig_becomes_cyrillic():
    assert latin_to_cyrillic("uws ruu 7honogiin aylal") == "увс рүү 7хоногийн аялал"
    assert latin_to_cyrillic("Увс нуур") == "Увс нуур"
