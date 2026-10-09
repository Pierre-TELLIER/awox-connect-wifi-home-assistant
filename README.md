# AwoX Connect Wifi Lights for Home Assistant

Control AwoX Connect Wi-Fi lights from Home Assistant: on/off, brightness, RGB colour and colour temperature. Lights report their state back to Home Assistant when they change.

> [!WARNING]
> This integration is not made, endorsed or supported by AwoX. It talks to AwoX's cloud using a protocol reverse-engineered from the Android app, so it can stop working if AwoX changes its service.

> [!CAUTION]
> Most of this repo is made by Claude. It has been tested, but be sure to keep in mind that this is experimental AI slop.


> [!CAUTION]
> Tested with one EGLO Bulb+ only. Other bulbs, bridges, firmware versions and multiple lights on one account are untested.

Based on [awox-connect-wifi](https://github.com/Pierre-TELLIER/awox-connect-wifi), which uses work from [fsaris/home-assistant-awox](https://github.com/fsaris/home-assistant-awox) for the initial authentication.

## Installation (HACS)

1. In HACS, open **Integrations → ⋮ → Custom repositories**.
2. Add `https://github.com/Pierre-TELLIER/awox-connect-wifi-home-assistant` with category **Integration**.
3. Find **AwoX Connect Wifi Lights**, click **Download**, then restart Home Assistant.

## Setup

1. Go to **Settings → Devices & services → Add integration** and search for **AwoX Connect Wifi Lights**.
2. Enter the email and password of your AwoX account. The integration checks them before saving.
3. Each light on the account appears as an entity, named after its name in the AwoX app.

The first start registers a new gateway in your AwoX account and creates the certificates. This takes a few seconds.

## Features

- On/off
- Brightness
- RGB colour
- Colour temperature
- State updates from the light when it changes (for example, when you use the AwoX app or a physical switch)

## Where data is stored

Inside your Home Assistant config folder:

- `awox/state.yaml`: the list of lights and their last known state
- `awox/certs/`: the certificates created for your account (the private key is readable only by you)

Removing the integration deletes the `awox` folder.

## Troubleshooting

| Message | Meaning |
| --- | --- |
| *Invalid email or password* | Check the credentials in the AwoX app. |
| *Could not reach the AwoX servers* | Check the internet connection, then try again. |
| *Setup failed* / retries in the log | Home Assistant retries automatically. See the log for the cause. |

To see detailed logs, add this to `configuration.yaml`:

```yaml
logger:
  logs:
    awox: debug
```

To start over (for example, after an account change), remove the integration and delete the `awox` folder in your config directory. Starting over registers another gateway in your AwoX account.

## Known limitations

- Each setup registers a new gateway in your AwoX account, and nothing removes old ones.
- Only one connection per account is possible. If you run the `awox` command-line tool with the same account at the same time, one of them will be disconnected.
- The colour-temperature range is an estimate (2000–6500 K), so the slider may not match the bulb's real range.
- Lights always show as available. Offline detection isn't implemented yet.
- Lights added to the AwoX app after setup only appear after you remove and re-add the integration.

## Updating

With HACS, open the integration, choose **⋮ → Redownload**, select the version you want, and restart Home Assistant.

## Development

The integration uses the [awox](https://github.com/Pierre-TELLIER/awox-connect-wifi) library, pinned in `manifest.json`. Changes to the library need a new pin there.
