import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from rich.console import Console

console = Console()


def send_email(cfg: dict, jobs: list):
    if not jobs:
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[ODK] {len(jobs)} nouvelles offres LinkedIn"
        msg["From"] = cfg["sender"]
        msg["To"] = cfg["recipient"]

        text_lines = [f"• {j['title']} chez {j['company']} ({j['location']})\n  {j['url']}" for j in jobs]
        plain = "Nouvelles offres :\n\n" + "\n\n".join(text_lines)

        html_rows = "".join(
            f"<tr><td><a href='{j['url']}'>{j['title']}</a></td>"
            f"<td>{j['company']}</td><td>{j['location']}</td>"
            f"<td>{'✅ Easy Apply' if j['easy_apply'] else ''}</td></tr>"
            for j in jobs
        )
        html = f"""<html><body>
        <h2>Nouvelles offres LinkedIn ({len(jobs)})</h2>
        <table border='1' cellpadding='6' cellspacing='0'>
          <tr><th>Poste</th><th>Entreprise</th><th>Lieu</th><th></th></tr>
          {html_rows}
        </table>
        </body></html>"""

        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as server:
            server.starttls()
            server.login(cfg["sender"], cfg["password"])
            server.sendmail(cfg["sender"], cfg["recipient"], msg.as_string())

        console.print(f"[green]Email envoyé à {cfg['recipient']} ({len(jobs)} offres)[/green]")
    except Exception as exc:
        console.print(f"[red]Erreur envoi email:[/red] {exc}")
