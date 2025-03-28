# lightnovelworld

This is rather a simple scraper as it doesn't get anything fancy as covers, synopsis, ratings, comments.

## Pestilence

Recently I've read a manhwa that was unfinished so I've decided to read the novel. It's quite a short one as it has around 200 chapters and is complete.

I've searched my data from [novellive](https://novellive.com) which has 1768649 files and weights 15GB. After finding it i've noticed that some chapters don't have all paragraphs saved, and that's not surprising as I didn't test much of the scripts output, being satisfied with a couple of novels.

Instead of fixing an old script I've decided to make a new one for some other site. I've found the [webnovel.com](https://www.webnovel.com) and the bad interface with multitude of api calls combined with ridiculous "protection" from users accessing the dev tools was enough to deter me.

I've just wanted to make a quick and pleasant to write script. Later I've found the [lightnovelworld.com](https://www.lightnovelworld.com).

The access to it was blocked to me on firefox by cloudflare making endless verification loop. This issue subsided on private mode. Interface of it had a lot of information and didn't use any api calls.

Knowing that such aggressive cloudflare would mean that I've would have to copy cookies from the browser any time I were to use script so I've searched github for existing scrapers.

I've found the [Novel-Grabber](https://github.com/Flameish/Novel-Grabber) and even though I've wanted to download just one novel I could not. cloudflare disease blocked any requests, I've tried copying the cookies from the browser through their terrible interface but it didn't help.

Forced to drastic measures I've quickly made the `lightnovelworld_old` script in bash. It had a lot of problem's with being blocked so I've made waiting time of around 7 seconds for each request. Still 10% of requests was getting randomly blocked, most of them also got stretched by long connection time, and then after 60 of them I needed to get new cookies.

Chapter files have to be named reasonably to be useful, but to get the title you have to download the page. So if some chapters failed in between you had to slowly redownload the whole thing anew. This was fixed by using the hash of url as file name and after downloading, setting their names to the first line in them which is the title.

After downloading 80% of chapters cloudflare got even more aggressive and worked only for 4 requests at a time.

Being unable to progress further I've rewritten it to python. Curl being executed as a command has no way of saving the connection so it has to reconnect for every request, and that was triggering the protection.

As i was already having problem with detection I've initially used the `curl_cffi` instead of `requests` to avoid tls fingerprinting, however it didn't make connection stay alive so I've switched back to `requests`.

To automatically get cookies from browser I've used the `browser_cookie3` lib, unfortunately it cannot get cookies from the private mode so I had to fix the endless verification loop on firefox. After defaulting the settings and turning the add-ons I've found that the problem was only with `Universal Bypass` since cloudflare for some reason really cares that my browser has the same user agent as the one it serves. It's weird that something like `Privacy Badger` or `NoScript` wasn't the cause.

I don't know why they protect those novels so much, each one of those sites stole it from the other anyway and now they care if some actual browser made 2 requests too quickly.

Now script doesn't have problems with downloading novels without any interruptions, although the waiting time is quite conservative.

If you want your chapters to be named by their title run this after downloading:

    find . -type f -regextype egrep -regex '.*/[0-9a-z]{64}' | xargs -I {} /bin/sh -c 'mv "{}" "$(dirname "{}")/$(head -n1 "{}")"'

## usage

Download chapter, novel, or pages of novels from `URL`s to `DIR`

    lightnovelworld --directory DIR URL1 URL2 URL3

Explicitly treat `URL`s to be of certain types, `URL5` and `URL6` will be guessed

    lightnovelworld --chapter URL1 --novel URL2 --chapters URL3 --pages URL4 URL5 URL6

Download a novel, this will create directory `Shadow Slave`, and inside of it chapters will be written named by `sha256` of their urls. Running this command in directory where it has already been downloaded will ommit downloaded parts.

    lightnovelworld 'https://www.lightnovelworld.com/novel/shadow-slave-05122222'

Download guessing from URL with waiting `2.5` seconds and randomly waiting up to `1500` miliseconds for each request

    lightnovelworld --wait 2.5 --wait-random 1500 URL

Download from `URL` using `4` retries and waiting `60` seconds between them

    lightnovelworld --retries 4 --retry-wait 60 URL

Download `URL` with timeout set to `60` seconds and custom user-agent

    lightnovelworld --timeout 60 --user-agent 'I AM NOT A BOT'

Choose browser from which cookies will be extracted (same names as for `browser_cookie3` lib)

    lightnovelworld --browser firefox URL

Get some help

    lightnovelworld --help
