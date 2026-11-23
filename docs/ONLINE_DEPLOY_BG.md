# SolarTree AI: GitHub + Render + Neon PostgreSQL

Тази версия е подготвена за **един Render web service**, който публикува React и FastAPI от един HTTPS адрес. Базата е **Neon PostgreSQL**.

## 1. Важни факти

- GitHub не изпълнява постоянно Python. Служи за кода и автоматично публикуване след промени.
- Render Free може да приспи приложението след 15 минути. За непрекъсната достъпност изберете платения **Starter** план (ориентировъчно $7/месец без други такси).
- Neon Free предоставя управляван PostgreSQL с безплатни лимити. При изчерпване на лимитите може да се наложи платен план.
- **Не публикувайте** `.env`, API ключове, токени за QR сдвояване, пароли или `solartree.db` в GitHub. Хранилището трябва да бъде private.
- За продукционен режим `DEMO_MODE=false` — без фиктивни профили, фиктивни дървета и симулации.

## 2. Neon PostgreSQL

1. Създайте акаунт в https://console.neon.tech и проект `solartree-ai`.
2. От **Connect** копирайте connection string, включително `sslmode=require` (или по-строги условия, предоставени от Neon). Пример без истински данни:
   `postgresql://user:password@ep-example-pooler.eu-central-1.aws.neon.tech/solartree?sslmode=require`
3. **Не поставяйте URL в GitHub.** Ще го въведете в Render като secret environment variable `DATABASE_URL`.
4. Backend-ът използва SQLAlchemy + psycopg. При **първо стартиране на празна база** създава таблиците `users`, `trees`, `readings`, `alerts`, `maintenance`, `device_registrations`, `mobile_pair_sessions`, `device_samples`.
5. SQLite архивът от вашия компютър **не се прехвърля автоматично** в Neon. Ако искате старите профили и устройства, е необходим отделен контролиран импорт. Не копирайте `.db` в GitHub.

## 3. GitHub

1. Влезте в https://github.com, създайте **private** repository `solartree-ai`.
2. Качете съдържанието на папката `SolarTree_AI_Project` (така че `Dockerfile` и `render.yaml` да са в корена на репозитория).
3. По възможност използвайте Git от VS Code:

   ```powershell
   git init
   git add .
   git status
   git commit -m "Prepare SolarTree AI for online deployment"
   git branch -M main
   git remote add origin https://github.com/USERNAME/solartree-ai.git
   git push -u origin main
   ```

   Заменете `USERNAME` със своя GitHub акаунт; свържете новия празен GitHub repo с `git remote add`.
4. **Преди `git add`** проверете, че няма `.env`, `.db`, реални ключове и други секрети. Проверете повторно с `git status`.

## 4. Render

1. Влезте в https://dashboard.render.com/ и свържете GitHub репозитория.
2. Изберете **New > Blueprint** (проектът съдържа `render.yaml`) или създайте Docker Web Service от същия repository.
3. За непрекъсната работа е избран план `starter` в `render.yaml`; той е платен. Ако искате първо безплатен тест, променете `plan: starter` на `plan: free` и приемете, че може да приспива услугата.
4. Въведете стойности на тайните настройки в Render:
   - `DATABASE_URL`: connection string от Neon (не публично).
   - `SECRET_KEY`: дълга случайна постоянна тайна — Render може да я генерира; **не я сменяйте при всяко рестартиране**, защото ще прекратява потребителските сесии.
   - `OPENAI_API_KEY`: по желание; необходими са отделно финансиране и лимит за AI услугата.
   - `APP_ENV=production`, `DEMO_MODE=false` са в Blueprint.
5. След успешна компилация вземете публичния адрес, например `https://solartree-ai.onrender.com`.
6. В Render > Environment добавете `PUBLIC_SCANNER_URL` със **същия HTTPS адрес**; redeploy/restart.
7. Отворете `https://<вашият адрес>/api/health` и после началната страница. Първо регистрирайте потребител; проверете вход и изход.
8. За сканирането с телефон използвайте временното сдвояване от приложението. Публичният HTTPS адрес трябва да съвпада с `PUBLIC_SCANNER_URL`.

## 5. Какво се записва

- `users`: имейл, име, **хеш** на паролата, роля.
- `trees`: модел, собственик, сериен номер, позиция.
- `readings`/`device_samples`: стойности от датчици и произход.
- `device_registrations`: **хешове** на отделните ключове за сдвояване/телеметрия.
- `mobile_pair_sessions`: краткотрайни QR сесии.
- `alerts`, `maintenance`: известия и обслужване.

## 6. Свързване на физическо дърво

- Pico 2 W изпраща JSON по HTTPS към `https://<вашият адрес>/api/device/<SERIAL>/sensors`.
- Устройството се регистрира предварително чрез **защитен операторски инструмент**, с еднократен claim token и отделен telemetry key, а не чрез свободен публичен QR.
- Водородните защитни системи остават независими от уеб приложението.
- В продукционен режим няма автоматично добавени тестови дървета; ако устройството още не е подготвено с валиден ключ, QR кодът му няма да може да бъде заявен.

## 7. Важни ограничения преди истински потребители

Това е **подготвен за публикуване пилотен проект**, не завършена защитена общинска услуга. За реална обществена употреба трябва допълнително: потвърждение на имейла, възстановяване на парола, rate limiting и защита от злоупотреби, автоматизирани миграции на PostgreSQL (Alembic), мониторинг, архивиране и възстановяване, политики за лични данни (GDPR), преглед на правата за общински оператори, отделно безопасно сервизно генериране на QR/telemetry keys.

При първо стартиране върху **празна** PostgreSQL база SQLAlchemy създава таблиците. За следващи промени по схемата е нужна Alembic миграция. Не разчитайте само на `create_all()` за обновяване на съществуващи таблици.
