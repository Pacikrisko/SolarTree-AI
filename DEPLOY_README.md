# SolarTree AI — готово за GitHub + Render + PostgreSQL

1. Публикувайте **private** GitHub repository (съдържанието на тази папка).
2. Създайте база Neon PostgreSQL.
3. Свържете GitHub в Render и създайте Blueprint от `render.yaml`.
4. В Render задайте `DATABASE_URL`, `SECRET_KEY` и по желание `OPENAI_API_KEY`.
5. При готов HTTPS адрес задайте `PUBLIC_SCANNER_URL` и проверете `/api/health`.

**Пълно ръководство на български:** `docs/ONLINE_DEPLOY_BG.md`

Локалният Windows стартер, SQLite режимът и разработката с `npm run dev` остават съвместими.
