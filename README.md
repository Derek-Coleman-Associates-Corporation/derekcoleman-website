# derekcoleman-website

Personal landing site for **derekcoleman.com**. A trimmed clone of the
[dcassociatesgroup-website](https://github.com/Derek-Coleman-Associates-Corporation/dcassociatesgroup-website)
stack, built as the dry-run vehicle for the dcassociatesgroup.com
M365→Azure DNS migration (see `MIGRATION-PLAYBOOK.md` once written).

## Stack

- `build.py` — stdlib-only static site generator → `public/`
- `api/` — Azure Static Web Apps managed functions (Node 20);
  `POST /api/contact` writes to Table `contactform` + Queue `contactform-notify`
  on this site's own storage account (app setting `CONTACT_STORAGE_CONNECTION`)
- `.github/workflows/deploy.yml` — GitHub Actions →
  `Azure/static-web-apps-deploy@v1` using repo secret
  `AZURE_STATIC_WEB_APPS_API_TOKEN`

## Azure resources

- Resource group `rg-derekcoleman-site` (eastus2)
- Static Web App (Free tier)
- Storage account (table + queue for the contact form)
- Azure DNS zone `derekcoleman.com`

## Build locally

```sh
python3 build.py   # writes public/
```
