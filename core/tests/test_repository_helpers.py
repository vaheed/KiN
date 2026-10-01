from app.repositories import _vector_literal


def test_vector_literal():
    assert _vector_literal([0, 0.5, 1]) == "[0,0.5,1]"
