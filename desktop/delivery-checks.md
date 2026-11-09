# Checked website delivery — beta.22 local preview

Set success criteria, run browser checks, review repair candidates, accept the delivery and save decisions for the next task. Desktop, Web and CLI share the same records when they use the same data workspace.

## Beginner workflow

1. Create or choose a task. Open **Delivery checks** in Desktop or **Delivery checks & handoff** in Web.
2. Enter a delivery name and goal. List the HTML entry file and every CSS, JavaScript, image or font asset the website needs. The initial template uses `index.html`. Optional **Human acceptance requirements** describe requirements that still need your judgment.
3. Optionally expand **Key interactions**. Give each check a name, a CSS selector to click, a result selector that must become visible, and optional expected text. Each interaction starts from a fresh page load. Choose zero, one or two optional repair rounds.
4. **Save criteria**. Saved criteria collapse into a compact editor. Sending the task includes the reviewed criteria in the model's context. Each task uses the criteria recorded when it starts. A concurrent edit prompts you to review the latest version and keeps your form text.
5. Generate the website, then review and save its output files. Checks use the files you saved.
6. Choose **Run checks**. This step runs entirely in the browser checker. Inspect the desktop/mobile results, actual screenshots, output hashes and any failed or unverified checks.
7. If needed, choose **Check & propose repairs** and explicitly authorize it. Failed checks can trigger at most the selected zero-to-two coding-model requests. Pantheon sends the listed text files and failed-check details to the task's coding-role model. A task-specific assignment takes priority over workspace defaults. The repair prompt includes the approved project-state snapshot, so confirmed project decisions participate in the repair. Changing that state before a repair or candidate apply requires fresh checking. Existing request/cost limits apply cumulatively across repair attempts. CLI repairs use the specified `--config` or the workspace coding-role defaults. Model/API failures retain actual earlier check evidence. Pantheon rechecks each candidate and waits for your approval to apply it.
8. Open **Review candidate differences**. A candidate can pass checks while the project still contains the original files. **Apply reviewed candidate** checks the original file hashes again before changing the declared text files. An external file or criteria change requires fresh checks. If a multi-file apply fails, Pantheon attempts to roll back its writes while preserving external edits. You can inspect the original snapshot and check evidence.
9. **Accept delivery** is separate from automated checks. All recorded automated checks must pass for the current file version. If you specified human requirements, explicitly acknowledge reviewing them and the actual output. A file or criteria change invalidates acceptance.
10. Review **Prepare the next handoff**. Edit the suggested decisions, next steps, check summary and output references. **Confirm project updates** applies these facts once, with the current project revision. Only this explicit confirmation makes entered decisions confirmed project facts.

A task finishing, automated checks passing and the user accepting the delivery are separate statuses. Open **Result → Checks & open items** in Desktop to see the recorded outputs, differences, checks, unresolved issues and acceptance.

## What checks establish

The checker supports **small static websites** composed of explicitly listed files.

- Entry HTML opens in a real browser at desktop 1440×900 and mobile 390×844 viewport sizes.
- Horizontal overflow is measured, configured interaction outcomes are observed, and uncaught page errors are recorded.
- Each check runs against an immutable file snapshot in a fresh browser context. Each interaction resets browser storage on a fresh navigation. Screenshots and file hashes identify the observed version.
- Only approved snapshot files are served. External/undeclared HTTP dependencies, service workers, downloads and WebSocket connections are blocked. Live services, accessibility audits and additional browsers or devices require separate checks.
- A blocked dependency or unavailable browser remains **unverified**. Recorded browser observations determine the verification status.

The checker isolates the listed website files at the browser level. Repair calls produce text candidates for review.

At most 32 approved files, 8 MiB total, 4 MiB per file, eight interaction checks and two repair requests are supported per delivery. Private/hidden paths, parent traversal, symlinks and unsupported asset types are rejected. Text repair input is bounded to 180 KB and returned replacement files to 200 KB each. Each browser worker is bounded to 100 seconds. An in-flight model request follows the existing provider timeout. An interrupted job retains evidence and requires deliberate fresh checking.

Each workspace retains up to 30 evidence runs. **Remove this evidence** deletes the selected report, snapshots and screenshots. Workspace backups include these evidence files.

## Browser availability

Desktop packages include the checker library and use an installed Chrome, Edge or an existing Playwright Chromium. It opens a fresh browser context. If no supported browser starts, the result stays unverified with setup guidance.

For a source Web/CLI installation, install the optional checking support from the checked-out source:

```bash
python -m pip install -e ".[checks]"
python -m playwright install chromium
```

Alternatively, use an installed Chrome or Edge. Linux may also require browser system libraries. [Playwright's browser setup instructions](https://playwright.dev/python/docs/browsers)

## CLI

Save the criteria below as `website-checks.json`.

```json
{
  "title": "Product website",
  "goal": "Explain the product and support the Add button",
  "entrypoint": "index.html",
  "files": ["index.html", "style.css"],
  "requirements": ["Use the agreed brand colors"],
  "interactions": [
    {"label": "Add updates the total", "click": "#add", "expect": "#total", "text": "1"}
  ],
  "repair_rounds": 2
}
```

Run the commands below from the selected project workspace.

```bash
pantheon delivery --contract website-checks.json --context product-website
pantheon delivery --context product-website --run
pantheon delivery --context product-website --run --repair
pantheon delivery --report RUN_ID
pantheon delivery --report RUN_ID --raw
pantheon delivery --apply RUN_ID
pantheon delivery --accept RUN_ID
pantheon delivery --stop RUN_ID
```

`--repair`, `--apply` and `--accept` require explicit interactive confirmation. Checks return exit code 2 for failed, unverified or candidate-only evidence. The normal report prints a summary, check rows and the evidence directory. Use `--raw` for the complete JSON record. To include a saved contract in generation, use `pantheon ask --delivery CONTRACT_ID "Build the product website"`.

For handoff, inspect suggestions with `pantheon delivery --handoff RUN_ID`. Save the reviewed entries in a JSON array.

```json
[
  {"kind": "decision", "text": "Use the approved sage brand color"},
  {"kind": "todo", "text": "Add a pricing page"},
  {"kind": "output", "text": "Current website", "file_path": "index.html"}
]
```

Apply the reviewed entries with this command.

```bash
pantheon delivery --handoff RUN_ID --updates reviewed-updates.json
```

## Local preview and evidence

The screenshots and verification below use isolated fixture projects, actual browser checks and a localhost model fixture, with zero paid API requests. The native preview evidence covers macOS on Apple Silicon.

The review panels show the criteria, observed failures and accepted evidence. [Criteria](../docs/desktop/delivery/criteria-light.png), [actual failures](../docs/desktop/delivery/observed-failures.png), [candidate differences](../docs/desktop/delivery/candidate-differences.png), [accepted delivery](../docs/desktop/delivery/delivery-overview-light.png), [Web](../docs/desktop/delivery/web-delivery.png), [dark](../docs/desktop/delivery/delivery-dark.png), [narrow Desktop](../docs/desktop/delivery/delivery-narrow.png), [narrow Web](../docs/desktop/delivery/web-delivery-narrow.png), [mobile screenshot evidence](../docs/desktop/delivery/accepted-evidence-light.png).

The beta.22 build is a local preview. [Verification record](verification.md)
