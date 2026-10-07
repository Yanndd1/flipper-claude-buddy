# Guide utilisateur — Flipper Claude Buddy (Windows)

> Ton Flipper Zero devient **télécommande + écran d'état + valideur de permissions** pour Claude Code. Tout passe par USB.

---

## 1. À quoi ça sert ?

Pendant que Claude Code travaille pour toi, plusieurs choses se passent en parallèle : commandes Bash à autoriser, fins de tâches, erreurs, plans à valider, questions ouvertes. Si tu fais autre chose à côté, tu rates ces signaux et Claude reste bloqué.

Avec ce système :

| Tu reçois… | …sur le Flipper |
|---|---|
| Une demande de permission Bash/Edit/Write | 🔐 LED + son + écran affiche `Bash` / projet / commande. **OK = autoriser**, **Back = refuser** |
| Une fin de tâche | ✅ Son "success" + écran "Turn complete / X tools" |
| Une erreur de tool | ⚠️ Son "error" + écran "Tool failed / mon-projet: ToolName" |
| Une session resumée | 🐬 Son "connect" + écran "Claude Code / Resumed" |
| Un sous-agent terminé | 🎵 Son "task_complete" + écran "Task done / nom" |

Et **tu pilotes** Claude depuis les boutons Flipper :

| Bouton | Action côté PC |
|---|---|
| **OK** (court) | Envoie **Enter** ⏎ |
| **OK** (long) | Tape "yes" puis Enter |
| **LEFT** (court) | **Escape** |
| **LEFT** (long) | **Ctrl+C** (interruption) |
| **RIGHT** (long) | Ouvre le **menu des slash commands** (130 commandes ; tu navigues UP/DOWN, OK pour insérer) |
| **DOWN** (court) | Flèche bas ↓ |
| **BACK** (court) | Backspace ⌫ |
| **BACK** (long) | Quitte l'app sur le Flipper |
| **UP** (court) | Voice / Dictée — *non disponible sous Windows* |

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Claude Code (terminal)                                 │
│  ├─ 10 hooks Python (~/.claude/settings.json)           │
│  │   SessionStart, Stop, PermissionRequest, …           │
│  └─ Chaque hook  ─── TCP 127.0.0.1:47353 ──┐            │
└──────────────────────────────────────────────│──────────┘
                                              ▼
┌─────────────────────────────────────────────────────────┐
│  Bridge daemon (Python 3.13, sans console)              │
│  %USERPROFILE%\flipper-claude-buddy-win\plugin\         │
│         host-bridge\bridge\__main__.py                   │
│  ├─ IPC TCP côté hooks                                  │
│  ├─ Win32 SendInput pour keystroke forwarding           │
│  ├─ Serial CLI ←→ Flipper                               │
│  └─ Auto-spawn par le hook SessionStart                 │
└──────────────────────────────────────────────│──────────┘
                                              ▼ USB CDC (COM15)
                              JSON v1 newline-delimited
                              {"v":1,"t":"perm","d":{...}}
                                              ▼
┌─────────────────────────────────────────────────────────┐
│  Flipper Zero — app .fap "Claude Buddy" v0.6            │
│  /ext/apps/USB/claude_buddy.fap                          │
│  ├─ Affiche état/permission sur l'écran                 │
│  ├─ Lit boutons et envoie en JSON                       │
│  └─ Patterns son + vibration + LED                      │
└─────────────────────────────────────────────────────────┘
```

3 composants installés :

| Composant | Emplacement |
|---|---|
| App Flipper `.fap` | `/ext/apps/USB/claude_buddy.fap` sur la SD du Flipper |
| Bridge + hooks Python | `%USERPROFILE%\flipper-claude-buddy-win\plugin\` |
| Config hooks Claude Code | `%USERPROFILE%\.claude\settings.json` (section `hooks`) |

Le bridge se lance **automatiquement** quand tu démarres une session Claude Code (via le hook `SessionStart` — il vérifie qu'il tourne, sinon il le démarre lui-même). Il s'arrête quand toutes les sessions sont closes (refcount).

---

## 3. Utilisation au quotidien

### Étape 1 — Lance l'app sur le Flipper
Sur l'appareil : `Menu → Apps → USB → Claude Buddy` → l'app affiche son écran d'accueil avec la startup fanfare.

### Étape 2 — Démarre Claude Code normalement
Dans ton terminal habituel : `claude` (ou ouvre la session). Au démarrage, tu vois sur le Flipper :
- Son "connect"
- Écran : `Claude Code / New session` (ou `Resumed`)

À partir de là, **tout est automatique** : permissions, fins de tâches, etc. apparaissent sur le Flipper sans intervention.

### Étape 3 — Tu interagis quand c'est nécessaire
- **Une permission Bash arrive** → OK = autoriser, Back = refuser
- **Tu veux taper Enter sans toucher le clavier** → OK
- **Tu veux interrompre Claude** → LEFT long (Ctrl+C)
- **Tu veux lancer `/agents` sans taper** → RIGHT long → choisir `/agents` dans le menu

### Étape 4 — Fin de journée
Ferme tes sessions Claude Code, le bridge se ferme tout seul.

---

## 4. Multi-projets — qui demande quoi ?

Si tu as plusieurs sessions Claude Code ouvertes (un projet par fenêtre), **chaque notification Flipper est préfixée par le nom du projet** :

| Sans préfixe (avant) | Avec préfixe (maintenant) |
|---|---|
| Titre `Bash`<br>Sous-titre `dir C:\Users\...` | Titre `Bash`<br>Sous-titre **`Japan_2_: dir C:\...`** |
| `Turn complete`<br>`1 Edit 2 Bash` | `Turn complete`<br>**`Japan_2_: 1 Edit 2`** |

Le préfixe est extrait automatiquement du `cwd` (current working directory) que chaque hook reçoit dans son payload. Tronqué à 8 caractères pour rester dans les 21 cars max du protocole.

> **Limitation actuelle** : si plusieurs sessions envoient des notifs en même temps, elles sont traitées en **FIFO** (file unique). Pas de "ligne dédiée par projet". Mais grâce au préfixe, tu sais toujours qui est l'expéditeur.

---

## 5. Personnalisation

### Préférences en `~/.claude/settings.json`
La section `pluginConfigs.flipper-claude-buddy.options` permet de configurer :

```json
"pluginConfigs": {
  "flipper-claude-buddy": {
    "options": {
      "bluetoothName": "NOM_BLUETOOTH_DU_FLIPPER",
      "serial_port": "",
      "transport": "auto"
    }
  }
}
```

- `bluetoothName` — auto-détecté au premier `hello`, utilisé pour BLE
- `serial_port` — laisse vide pour auto-détection. Sinon ex: `"COM15"`
- `transport` — `"auto"` (recommandé), `"usb"` ou `"ble"`

### Slash commands sur le Flipper
Le menu intégré (RIGHT long) charge automatiquement :
1. Tous les built-in Claude Code (`/help`, `/clear`, `/agents`, etc.) — 69 commandes
2. Toutes les commandes de tes plugins activés dans `enabledPlugins`
3. Tes skills personnels dans `~/.claude/skills/*/SKILL.md`
4. Les commandes spécifiques au projet courant dans `<project>/.claude/commands/*.md`

**Mise à jour** : à chaque démarrage de session, le bridge recharge la liste. Donc ajouter un nouveau plugin = redémarrer la session Claude Code.

### Ajout de commandes personnelles
Crée `~/.claude/flipper-commands.txt` :
```
/mon-raccourci-1
/mon-raccourci-2
```
Elles apparaîtront dans le menu Flipper.

---

## 6. Dépannage

### "Le bridge ne démarre pas"
1. Vérifier qu'aucun autre process ne tient COM15 (qFlipper, terminal serial…)
2. Voir le log : `Get-Content $env:TEMP\claude-flipper\claude-flipper-bridge.log -Tail 30`
3. Forcer relance : `Get-Process | Where-Object { $_.Path -like "*Python313*" } | Stop-Process` puis redémarrer une session Claude

### "L'app sur le Flipper ne reçoit rien"
1. Vérifier que **l'app .fap est lancée** sur le Flipper (Apps → USB → Claude Buddy)
2. Vérifier dans le log du bridge la ligne `Flipper connected: fw=0.1.0 bt=...`
3. Si le bridge reçoit le banner CLI au lieu de JSON, c'est que la `.fap` n'est pas en avant-plan sur le Flipper

### "Les touches n'arrivent pas dans la fenêtre PC"
- Le keystroke arrive dans la **fenêtre qui a le focus** au moment de l'appui. Ce n'est pas forcément Claude Code.
- Pour Notepad ou apps lentes, il y a un délai de 12ms par caractère côté bridge — si ça reste lent, augmente la valeur dans `bridge\input.py` (fonction `_send_unicode_text`).

### "Les permissions s'auto-acceptent sans passer par le Flipper"
- Claude Code a un classifier auto-mode qui décide en amont. Les commandes considérées safe ne déclenchent pas le hook `PermissionRequest`. C'est volontaire.
- Pour forcer le passage : retire les permissions auto dans `~/.claude/settings.local.json` (`permissions.allow`).

### Vérifier que tout tourne
```powershell
# Le bridge tourne ?
Get-Process | Where-Object { $_.Path -like "*Python313*" } | Select Id

# Le port TCP IPC répond ?
py -3.13 -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('127.0.0.1', 47353)); print('OK'); s.close()"

# Envoyer une notif test
py -3.13 -c "import socket, json; s=socket.socket(); s.connect(('127.0.0.1', 47353)); s.sendall(json.dumps({'action':'notify','sound':'success','vibro':True,'text':'Test','subtext':'OK'}).encode()); s.shutdown(socket.SHUT_WR); print(s.recv(4096).decode())"
```

---

## 7. Sécurité et bonnes pratiques

- **Tout reste en local** — TCP localhost + USB. Rien ne sort de ta machine.
- **Failover propre** — Si le bridge n'est pas joignable ou que le Flipper n'est pas connecté, le hook `permission-request` renvoie un statut "ask" → Claude Code affiche son dialog habituel et tu réponds depuis le terminal. **Pas de blocage.**
- **Refcount sur les sessions** — Le bridge ne tourne que quand au moins une session Claude Code est ouverte.

---

## 8. Migration depuis la v2

Si tu reviens à notre v2 maison :
- Backup v2 : `%USERPROFILE%\flipper-claude-v2-backup\`
- Pour revenir : remplace le bloc `hooks` dans `~/.claude/settings.json` par les anciens hooks pointant vers `%USERPROFILE%\.claude\hooks\flipper_notify.py`, et arrête le bridge actuel.

Mais aucune raison de revenir — v3 a 5× plus de fonctions et le texte affiché à l'écran.

---

## 9. Référence rapide

| Action | Commande |
|---|---|
| Voir le log bridge | `Get-Content $env:TEMP\claude-flipper\claude-flipper-bridge.log -Tail 20 -Wait` |
| Tuer le bridge | `Get-Process \| Where-Object { $_.Path -like "*Python313*" } \| Stop-Process` |
| Tester ping bridge | `py -3.13 -c "import socket; s=socket.socket(); s.connect(('127.0.0.1', 47353)); print('OK')"` |
| Mettre à jour la `.fap` | Télécharge le nouveau release Buddy puis recopie via qFlipper ou `push_fap.py` |
| Voir les commandes chargées dans le menu | Le log du bridge dit `Loaded 130 commands (69 built-in + 61 custom)` |

| Fichier | Rôle |
|---|---|
| `%USERPROFILE%\flipper-claude-buddy-win\plugin\host-bridge\bridge\` | Code du bridge |
| `%USERPROFILE%\flipper-claude-buddy-win\plugin\scripts\` | Hooks Python |
| `%USERPROFILE%\.claude\settings.json` | Config Claude Code (hooks + plugin options) |
| `%TEMP%\claude-flipper\` | Fichiers runtime (log, pid, refcount, turn stats) |
| `/ext/apps/USB/claude_buddy.fap` (sur Flipper) | App .fap v0.6 |

---

## 10. Différences avec macOS/Linux

| Feature | Windows (toi) | macOS/Linux (original) |
|---|---|---|
| IPC entre hooks et bridge | TCP `127.0.0.1:47353` | Unix socket `/tmp/claude-flipper-bridge.sock` |
| Keystroke forwarding | Win32 `SendInput` (ctypes) | `osascript` (macOS) / `xdotool` (Linux X11) |
| USB port detection | `pyserial.tools.list_ports` filtré sur VID `0483` / PID `5740` | Glob `/dev/cu.usbmodem*` ou `/dev/ttyACM*` |
| Dictation (UP button) | Désactivée — pas d'API native simple | macOS native, Linux custom |
| Plugin marketplace | Installation manuelle | `claude plugin install` (à tester) |
| Signaux asyncio | Désactivés (Windows ne supporte pas SIGINT via asyncio) | Activés |

Cette adaptation Windows a été codée à partir du fork upstream `jxw1102/flipper-claude-buddy` (MIT). Le code patché est dans `%USERPROFILE%\flipper-claude-buddy-win`.

---

*Document généré le 27/05/2026 · Flipper Claude Buddy v3 (port Windows) · Bridge Python 3.13 · App .fap v0.6*
