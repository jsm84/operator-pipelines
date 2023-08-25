from typing import Any, List
from unittest import mock
from unittest.mock import MagicMock, call, patch

import pytest
from github.Repository import Repository
from github import GithubException

from operatorcert.entrypoints.github_wait_labels import (
    main,
    WaitCondition,
    WaitType,
    get_pr_labels,
    setup_argparser,
    wait_on_pr_labels,
)


def test_setup_argparser() -> None:
    assert setup_argparser() is not None


@patch("operatorcert.entrypoints.github_wait_labels.wait_on_pr_labels")
@patch("operatorcert.entrypoints.github_wait_labels.Github.get_repo")
@patch("operatorcert.entrypoints.github_wait_labels.setup_logger")
@patch("operatorcert.entrypoints.github_wait_labels.setup_argparser")
@patch("operatorcert.entrypoints.github_wait_labels.exit")
def test_main(
    mock_sys_exit: MagicMock,
    mock_setup_argparser: MagicMock,
    mock_setup_logger: MagicMock,
    mock_github_get_repo: MagicMock,
    mock_wait_on_pr_labels: MagicMock,
    monkeypatch: Any,
) -> None:
    args = MagicMock()
    args.any = ["regexp1", "regexp2"]
    args.none = ["regexp3"]
    args.timeout = 3600
    args.poll_interval = 1

    args.pull_request_url = "https://github.com/foo/bar/pull/123"
    mock_setup_argparser.return_value.parse_args.return_value = args

    mock_repo = MagicMock()
    mock_github_get_repo.return_value = mock_repo()

    monkeypatch.setenv("GITHUB_TOKEN", "foo_api_token")

    main()

    # want to test with __eq__ here to avoid mocking
    assert mock_wait_on_pr_labels.call_args[0][2] == [
        WaitCondition(WaitType.WaitAny, "regexp1"),
        WaitCondition(WaitType.WaitAny, "regexp2"),
        WaitCondition(WaitType.WaitNone, "regexp3"),
    ]

    assert mock_wait_on_pr_labels.call_args[0][1] == 123
    assert mock_wait_on_pr_labels.call_args[0][3] == 3600
    assert mock_wait_on_pr_labels.call_args[0][4] == 1

    mock_sys_exit.assert_called_once_with(0)


@patch("operatorcert.entrypoints.github_wait_labels.wait_on_pr_labels")
@patch("operatorcert.entrypoints.github_wait_labels.Github.get_repo")
@patch("operatorcert.entrypoints.github_wait_labels.setup_logger")
@patch("operatorcert.entrypoints.github_wait_labels.setup_argparser")
@patch("operatorcert.entrypoints.github_wait_labels.exit")
def test_main_error(
    mock_sys_exit: MagicMock,
    mock_setup_argparser: MagicMock,
    mock_setup_logger: MagicMock,
    mock_github_get_repo: MagicMock,
    mock_wait_on_pr_labels: MagicMock,
    monkeypatch: Any,
):
    args = MagicMock()
    args.any = ["regexp1", "regexp2"]
    args.none = ["regexp3"]
    args.timeout = 3600
    args.poll_interval = 1

    args.pull_request_url = "https://github.com/foo/bar/pull/123"
    mock_setup_argparser.return_value.parse_args.return_value = args

    mock_repo = MagicMock()
    mock_github_get_repo.return_value = mock_repo()

    monkeypatch.setenv("GITHUB_TOKEN", "foo_api_token")
    mock_wait_on_pr_labels.return_value = False

    mock_sys_exit.side_effect = Exception("So that the utility terminates")

    with pytest.raises(Exception):
        main()

    mock_sys_exit.assert_called_once_with(1)


@patch("operatorcert.entrypoints.github_wait_labels.wait_on_pr_labels")
@patch("operatorcert.entrypoints.github_wait_labels.Github.get_repo")
@patch("operatorcert.entrypoints.github_wait_labels.setup_logger")
@patch("operatorcert.entrypoints.github_wait_labels.setup_argparser")
@patch("operatorcert.entrypoints.github_wait_labels.exit")
def test_main_get_repo_exception(
    mock_sys_exit: MagicMock,
    mock_setup_argparser: MagicMock,
    mock_setup_logger: MagicMock,
    mock_github_get_repo: MagicMock,
    mock_wait_on_pr_labels: MagicMock,
    monkeypatch: Any,
):
    args = MagicMock()
    args.any = ["regexp1", "regexp2"]
    args.none = ["regexp3"]
    args.timeout = 3600
    args.poll_interval = 1

    args.pull_request_url = "https://github.com/foo/bar/pull/123"
    mock_setup_argparser.return_value.parse_args.return_value = args

    mock_github_get_repo.side_effect = GithubException(0, "err", None)

    monkeypatch.setenv("GITHUB_TOKEN", "foo_api_token")
    mock_wait_on_pr_labels.return_value = False

    mock_sys_exit.side_effect = Exception("So that the utility terminates")

    with pytest.raises((GithubException, Exception)):
        main()

    mock_sys_exit.assert_called_once_with(2)


def test_get_pr_labels():
    mock_repo = MagicMock()
    labels = [MagicMock(), MagicMock()]
    for mock_label, label_name in zip(labels, ["label1", "label2"]):
        mock_label.name = label_name

    mock_pr = MagicMock()
    mock_pr.labels = labels
    mock_repo.get_pull.return_value = mock_pr

    assert get_pr_labels(mock_repo, 0) == ["label1", "label2"]


def test_get_wait_conditions():
    args = MagicMock()
    args.any = ["one", "two"]
    args.none = ["three"]

    assert WaitCondition.get_wait_conditions(args) == [
        WaitCondition(WaitType.WaitAny, "one"),
        WaitCondition(WaitType.WaitAny, "two"),
        WaitCondition(WaitType.WaitNone, "three"),
    ]


@pytest.mark.parametrize(
    ["wait_type", "regexp", "labels", "result"],
    [
        (WaitType.WaitAny, "test", ["test"], True),
        (WaitType.WaitAny, "test", ["one", "another-one", "hello", "test"], True),
        (WaitType.WaitAny, "test", ["test", "more-labels"], True),
        (WaitType.WaitAny, "test", [], False),
        (WaitType.WaitAny, "t..t", ["test"], True),
        (WaitType.WaitNone, "test", ["test"], False),
        (WaitType.WaitNone, "test", ["more-labels"], True),
        (WaitType.WaitNone, "test", ["one", "two", "three"], True),
        (WaitType.WaitNone, "test", ["one", "two", "test"], False),
    ],
)
def test_condition_holds(
    wait_type: WaitType, regexp: str, labels: list[str], result: bool
):
    condition = WaitCondition(wait_type, regexp)
    assert condition.holds(labels) == result


@pytest.mark.parametrize(
    ["pr_labels_sequence", "wait_conditions"],
    [
        pytest.param(
            [["label_one", "label_two"]],
            [WaitCondition(WaitType.WaitAny, ".*two")],
            id="any one label",
        ),
        pytest.param(
            [["label_one"], ["label_one", "label_two"]],
            [WaitCondition(WaitType.WaitAny, ".*two")],
            id="any one label repoll",
        ),
        pytest.param(
            [["label_one", "label_two"]],
            [
                WaitCondition(WaitType.WaitAny, "label_two"),
                WaitCondition(WaitType.WaitAny, "label_one"),
            ],
            id="any two labels",
        ),
        pytest.param(
            [["label_one"], ["label_one", "label_two"]],
            [
                WaitCondition(WaitType.WaitAny, "label_two"),
                WaitCondition(WaitType.WaitAny, "label_one"),
            ],
            id="any two labels repoll",
        ),
        pytest.param(
            [["label_one", "label_two"]],
            [WaitCondition(WaitType.WaitNone, "three")],
            id="none one label",
        ),
        pytest.param(
            [["label_one", "label_two"], ["label_one"]],
            [WaitCondition(WaitType.WaitNone, "label_two")],
            id="none one label repoll",
        ),
        pytest.param(
            [["label_one", "label_two"]],
            [
                WaitCondition(WaitType.WaitNone, "three"),
                WaitCondition(WaitType.WaitNone, "four"),
            ],
            id="none two labels",
        ),
        pytest.param(
            [["label_one", "label_two"], ["label_two"]],
            [
                WaitCondition(WaitType.WaitNone, "label_one"),
                WaitCondition(WaitType.WaitNone, "label_three"),
            ],
            id="none two labels repoll",
        ),
        pytest.param(
            [["label_one", "label_two"]],
            [
                WaitCondition(WaitType.WaitAny, "label_one"),
                WaitCondition(WaitType.WaitNone, "label_three"),
            ],
            id="mixed conditions",
        ),
        pytest.param(
            [["label_one", "label_two"], ["label_one"]],
            [
                WaitCondition(WaitType.WaitAny, "label_one"),
                WaitCondition(WaitType.WaitNone, "label_two"),
            ],
            id="mixed conditions repoll",
        ),
    ],
)
@patch("operatorcert.entrypoints.github_wait_labels.get_pr_labels")
def test_wait_on_pr_labels_success(
    mock_get_pr_labels: MagicMock,
    pr_labels_sequence: list[list[str]],
    wait_conditions: list[WaitCondition],
    capsys,
):
    mock_get_pr_labels.side_effect = pr_labels_sequence
    assert wait_on_pr_labels(None, None, wait_conditions, 5, 0.1)

    captured_stdout, _ = capsys.readouterr()
    assert captured_stdout == str.join("\n", pr_labels_sequence[-1]) + "\n"


@pytest.mark.parametrize(
    ["pr_labels", "wait_conditions"],
    [
        pytest.param(["label"], [WaitCondition(WaitType.WaitAny, "test")]),
        pytest.param(["label"], [WaitCondition(WaitType.WaitNone, "label")]),
    ],
)
@patch("operatorcert.entrypoints.github_wait_labels.get_pr_labels")
def test_wait_on_pr_labels_timeout(
    mock_get_pr_labels: MagicMock,
    pr_labels: list[str],
    wait_conditions: list[WaitCondition],
):
    mock_get_pr_labels.return_value = pr_labels
    assert not wait_on_pr_labels(None, None, wait_conditions, 1, 0.1)


@patch("operatorcert.entrypoints.github_wait_labels.exit")
def test_get_pr_labels_exception(mock_exit: MagicMock):
    mock_repo = MagicMock()
    mock_repo.get_pull.side_effect = GithubException(0, "err", None)

    mock_exit.side_effect = Exception("End program at exit")

    with pytest.raises((GithubException, Exception)):
        get_pr_labels(mock_repo, 0)

    mock_exit.assert_called_once_with(1)
