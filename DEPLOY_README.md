# SolarTree AI — готово за GitHub + Render + PostgreSQL

1. Публикувайте **private** GitHub repository (съдържанието на тази папка).
2. Създайте база Neon PostgreSQL.
3. Свържете GitHub в Render и създайте Blueprint от `render.yaml`.
4. В Render задайте `DATABASE_URL`, `SECRET_KEY` и по желание `OPENAI_API_KEY`.
5. При готов HTTPS адрес задайте `PUBLIC_SCANNER_URL` и проверете `/api/health`.

**Пълно ръководство на български:** `docs/ONLINE_DEPLOY_BG.md`

Локалният Windows стартер, SQLite режимът и разработката с `npm run dev` остават съвместими.


### Google sign-in

Create a Google Auth Platform OAuth client of type Web application and add the
public HTTPS origin of SolarTree under Authorized JavaScript origins. For the
current deployment use `https://solartree-ai.onrender.com`. Set
`GOOGLE_CLIENT_ID` on the Render web service to that client's public ID.
The Google button uses the popup callback and server-side ID token validation.
For an existing SolarTree email, confirm the SolarTree password once to link
the account. With no client ID configured, password login remains available.
