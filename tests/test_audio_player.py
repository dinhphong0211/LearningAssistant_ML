import audio_player


def test_html_embeds_audio_and_escapes_title():
    html = audio_player.build_html("id1", 'Bài </script><b>x</b>', b"\x00\x01\x02")
    assert "AAEC" in html                      # base64 của 3 byte
    assert html.count("</script>") == 1        # chỉ thẻ đóng thật, tiêu đề không phá được
    assert "<\\/script>" in html


def test_html_has_resume_and_lockscreen_hooks():
    html = audio_player.build_html("id1", "T", b"x")
    for needle in ("localStorage", "mediaSession", "seekto", "pagehide", "visibilitychange", "la:pos:"):
        assert needle in html


def test_palette_override():
    html = audio_player.build_html("id1", "T", b"x", {"amber": "#123456"})
    assert "--amber: #123456;" in html
