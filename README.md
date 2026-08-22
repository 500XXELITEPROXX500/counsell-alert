# 🚨 Counsell Alert

Independent GitHub Actions monitor for Chicago Cubs manager Craig Counsell media updates.

## Features
- Checks the official MLB Cubs manager-postgame feed every 10 minutes.
- Detects newly published Counsell clips.
- Flags likely injury, rehab, return, role and workload topics.
- Detects player names when they appear in source text.
- Sends iPhone push notifications through ntfy.
- Prevents duplicate alerts with stored state.
- Includes the original MLB link.
- Never labels an AI paraphrase as an exact quote.

## Phone notifications
1. Install the ntfy iPhone app.
2. Pick a private/random topic name.
3. In GitHub: Settings → Secrets and variables → Actions.
4. Add repository secret `NTFY_TOPIC` containing your private topic.
5. Add repository secret `NTFY_SERVER` with value `https://ntfy.sh`.

Keep the topic secret. Do not put it in this repository.

## Optional AI
The monitor works without AI. An `OPENAI_API_KEY` secret can be added later for richer classification/summaries. The system must not fabricate direct quotes.

## GitHub
The scheduled workflow is `.github/workflows/counsell-alert.yml`.
Create a new repository named `counsell-alert`, upload this project, then enable Actions.

## Manual test
Actions → Counsell Alert → Run workflow.

## Quote accuracy
MLB public video pages do not always expose a complete machine-readable transcript. This project therefore reports source titles/descriptions as source metadata and explicitly says when an exact quote is not verified.
