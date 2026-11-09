# Continue a project — beta.21 local preview

Pantheon's first continuity milestone keeps an explicit project state beside conversations: goals, confirmed decisions, current outputs, open items and check notes. Desktop and Web use the same core, API and workspace database. The English Desktop garden themes and Web temple artwork remain unchanged.

## Try it

1. Open a project and choose **Project overview** in Desktop, or **Project overview & continue** in Web.
2. Choose **Add project entry**. Add a goal, then a decision such as “Use forest green for this website.” Choose **confirmed** only when you have approved it. Candidates are visible for review but are excluded from current decision context.
3. Add a next step, such as a pricing page. Outputs explicitly saved through Web's file-save action or Desktop's reviewed-save action are registered automatically when safely inspectable. You can also register an existing project-relative output file.
4. In **Continue this project**, describe the next outcome and choose **Prepare new task**. Pantheon creates a fresh conversation and retains the previous unsent draft. It sends no model request. Review the new draft and send it deliberately.
5. Open the same workspace through the other interface. Refresh the overview: its decisions, todos and output references are shared. Two independent project folders or computers are not automatically synchronized; both clients must use the same workspace/server.

New dispatches read the current approved state. A running dispatch retains its initial state snapshot across planning and role execution. Existing chats are not rewritten. CLI dispatches in the same data workspace also read this shared context; the new editing interface is in Desktop and Web.

## Files and corrections

Only explicitly registered files are inspected; this is not a whole-project watcher or a complete Git diff. The overview compares bounded file hashes with registered baselines and reports **unchanged**, **changed**, **missing** or **unavailable**. Private paths, symbolic links and files over 4 MiB cannot be registered. An overview scan has a 16 MiB inspection budget; entries that cannot be inspected remain visibly unavailable. No file contents are stored in project state.

A prepared continuation records the reviewed project revision and file observations. If either changes before sending, submission stops before dispatch. Open the overview, inspect the latest state and choose **Review current draft**, or prepare another new task. **Accept current file version** updates only the recorded baseline: it does not change the file or pass a test.

**Edit**, **Delete**, **Replace decision** and **Mark done** make project state user-controlled. Replacing a confirmed decision supersedes the previous one. Deleted, superseded, candidate and completed entries are excluded from current context. Historical conversations and ordinary memory remain separately accessible; the model is instructed not to revive obsolete decisions from them. This context rule does not guarantee that every model obeys it, so review delivered work.

Concurrent saves use project identity and revision checks. A conflicting edit keeps its form text and displays the latest saved entry; review it before explicitly applying your retained edit. An edit from another workspace cannot be applied to the new workspace.

## Verification boundaries

Check notes are **user reports**, never independently passed checks. “File matches registered version” and “task execution completed” do not imply that a website works, a script passed tests or a delivery was accepted. At the beta.21 milestone, automated evidence collection and a bounded check/repair cycle were still pending; the subsequent [beta.22 website delivery milestone](delivery-checks.md) adds them for small static websites.

Project state is limited to 128 entries; context is bounded, prioritizes goals and confirmed decisions, and marks omissions. Ordinary memory notes and generated answers are not automatically promoted to confirmed decisions. Project state is included in existing workspace backups; registered output file contents still require the normal project-file backup.

Screenshots: [Desktop light](../docs/desktop/continuity/desktop-project-light.png), [Desktop dark](../docs/desktop/continuity/desktop-project-dark.png), [external file change](../docs/desktop/continuity/desktop-file-changed.png), [retained conflicting edit](../docs/desktop/continuity/desktop-edit-conflict.png), [Web](../docs/desktop/continuity/web-project-state.png), [narrow Web](../docs/desktop/continuity/web-project-narrow.png).

All screenshot content comes from isolated test projects and fixture models, not real user conversations or commercial account acceptance. Current local test results are recorded in [verification](verification.md). This source is a local preview; download availability is determined by actual Release assets.
