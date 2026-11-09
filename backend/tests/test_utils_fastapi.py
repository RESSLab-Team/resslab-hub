from resslab_hub.utils.fastapi import attachment


def test_attachment_plain_name():
    assert attachment("braces.csv") == (
        "attachment; filename=\"braces.csv\"; filename*=UTF-8''braces.csv"
    )


def test_attachment_cannot_break_the_header():
    """A name from a query must not end the value or add a field (#264 Low)."""
    header = attachment('a"; x=1\r\nSet-Cookie: s=1;b.csv')
    assert "\r" not in header and "\n" not in header
    assert header.count('"') == 2
    assert header.startswith('attachment; filename="a_x_1_Set-Cookie_s_1_b.csv"; ')
    assert header.endswith(
        "filename*=UTF-8''a%22%3B%20x%3D1%0D%0ASet-Cookie%3A%20s%3D1%3Bb.csv"
    )


def test_attachment_keeps_the_real_name_in_filename_star():
    header = attachment("éprouvette.csv")
    assert 'filename="_prouvette.csv"' in header
    assert "filename*=UTF-8''%C3%A9prouvette.csv" in header
