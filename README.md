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

## Posting to the blog

1. Create `content/posts/<slug>.md` with front-matter:

   ```markdown
   ---
   title: My Post Title
   date: 2026-07-15
   category: tech        # tech | finance | fitness
   excerpt: One-sentence summary shown on the card.
   image: assets/blog/my-image.png   # optional hero image
   ---

   Body in markdown: headings, lists, links, **bold**, `code`,
   fenced code blocks (```python … ```), and images:
   ![alt text](../../assets/blog/my-image.png)
   ```

2. Drop any images into `assets/blog/`.
3. Commit and push — CI rebuilds and deploys. The post appears at
   `/blog/<slug>/`, on the blog index, and on the home Discussions feed.

## Build locally

```sh
python3 build.py   # writes public/
```
