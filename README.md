## Bulk-ytdlp (Bot)

---

Telegram Bot to Bulk Downloading list of yt-dlp supported urls and Upload to Telegram.

### Features:

#### Upload list of urls (2 methods):

- send command `/link` and then send urls, separated by new line.
- send txt file (links), separated by new line.

<details>
<summary>
    <b style="font-size: 27px"> Environments </b>
</summary>
<br>

`API_HASH`: Get this from my.telegram.org

`APP_ID`: Get this from my.telegram.org

`BOT_TOKEN`: Get this from @BotFather on Telegram.

`AS_ZIP`: Set this to `true` if you want the bot to upload the files as zipfile. Default to `false`

`BUTTONS`: Set this to `true` if you want the bot to ignore `AS_ZIP` and send a button instead. Default to `false`

</details>

## Deployments:

<details>
<summary>
    <b> Docker </b>
</summary>
<br>

Install Docker

`curl -fsSL https://get.docker.com | sh`

Refresh User State

`sudo su -l $USER`

Running Docker Server

`docker run -d -e API_HASH=xxHASHIDxx -e APP_ID=xxAPPIDxx -e BOT_TOKEN="xxx:xxx" -e OWNER_ID=xxYOURIDxx -e AS_ZIP=false -e BUTTONS=true ghcr.io/chosomeister/bulk-ytlp:latest`

</details>


## Telegram Support:

(https://t.me/tayefi)

#### LICENSE

- GPLv3
