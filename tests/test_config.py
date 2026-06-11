from app.config import ENV_FILE, PROJECT_ROOT, Settings


def test_settings_env_file_is_project_root_absolute_path() -> None:
    assert ENV_FILE == PROJECT_ROOT / ".env"
    assert ENV_FILE.is_absolute()


def test_settings_default_env_file_does_not_follow_current_directory(
    monkeypatch,
    tmp_path,
) -> None:
    (tmp_path / ".env").write_text(
        "ADMIN_API_TOKEN=TOKEN_FROM_WRONG_WORKDIR\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)

    loaded_settings = Settings()

    assert loaded_settings.ADMIN_API_TOKEN != "TOKEN_FROM_WRONG_WORKDIR"
