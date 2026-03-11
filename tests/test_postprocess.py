from autonomos.postprocess import codexify_message


def test_codexify_message_removes_soft_openers():
    assert codexify_message("Got it - hello") == "hello"
    assert codexify_message("Sure, hello") == "hello"
