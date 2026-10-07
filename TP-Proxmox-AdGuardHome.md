# TP — Infra réseau PME et publication de `app.pme.lan` : procédure complète sous **Proxmox VE**

> Adaptation du TP écrit pour VMware Workstation. Les exigences E1 à E7, les missions et les livrables restent les mêmes. Seule la plateforme de virtualisation change.
> Système invité : **Debian 13 « Trixie »** (Debian 12 fonctionne aussi). Les commandes sont à exécuter en `root`, ou avec `sudo`.

---

## 0. Correspondance VMware Workstation → Proxmox VE

| VMware Workstation (énoncé) | Équivalent Proxmox VE (ce document) | Remarque |
|---|---|---|
| **VMnet2** (host-only, LAN isolé) | **`vmbr1`** : bridge Linux **sans port physique et sans IP** | Seules les VM y sont branchées. Ni l'hôte ni le réseau de l'établissement n'y ont accès. |
| **VMnet8** (NAT, WAN) | **`vmbr0`** : bridge par défaut, relié à la carte physique | Seul le routeur y est branché. Il reçoit une IP du réseau de l'établissement, puis fait lui-même le NAT. Voir l'option « fidèle VMnet8 » au § 1.3. |
| Carte réseau « e1000 / vmxnet3 » | Carte **VirtIO** | Dans Debian : `net0` → **`ens18`**, `net1` → **`ens19`** |
| Cloner une VM | **Template** + **Full clone** (`qm template`, `qm clone`) | Une seule installation Debian pour les 5 VM |
| Wireshark sur l'hôte ou dans la VM | Wireshark dans la VM cliente, **ou** `tcpdump` sur l'interface `tapXXXiY` de l'hôte | Pratique pour capturer côté WAN du routeur (preuve du NAT) |

---

## 1. Travail préparatoire (Mission 1 — Conception)

### 1.1 Plan d'adressage

Réseau LAN : **`192.168.10.0/24`** (privé, RFC 1918), domaine interne **`pme.lan`**.

| VMID | Machine (hostname) | Rôle | Interface → Bridge | Adresse IP | Mode |
|---|---|---|---|---|---|
| 101 | `r1-routeur` | Routeur + NAT/PAT | `ens18` → **vmbr0 (WAN)** | IP fournie par le réseau de l'établissement | DHCP (côté WAN) |
| | | | `ens19` → **vmbr1 (LAN)** | **192.168.10.1/24** | Statique |
| 102 | `srv-dhcp` | Serveur DHCP dédié | `ens18` → vmbr1 | **192.168.10.2/24** | Statique |
| 103 | `srv-dns` | Résolveur AdGuardHome | `ens18` → vmbr1 | **192.168.10.3/24** | Statique |
| 104 | `srv-web` | Serveur web on-premise (`app.pme.lan`) | `ens18` → vmbr1 | **192.168.10.4/24** | Statique |
| 105 | `client` | Poste utilisateur (XFCE + Firefox + Wireshark) | `ens18` → vmbr1 | **192.168.10.100 à 200** | **DHCP** |
| 100 | `debian13-base` | Template (modèle), jamais démarré en production | — | — | — |

**Justification du plan d'adressage**

- Les adresses **.1 à .49 sont réservées aux équipements à IP fixe** : passerelle en .1 (convention), puis les serveurs.
- La **plage DHCP va de .100 à .200**. Elle est disjointe des IP statiques, donc aucune collision n'est possible.
- Un **/24** offre 254 hôtes, largement assez pour une PME, et le calcul est simple.
- `192.168.10.0/24` a été choisi pour **ne pas chevaucher le réseau WAN** (celui de l'établissement, sur `vmbr0`). ⚠️ Vérifiez ce point : si l'établissement utilise déjà `192.168.10.0/24`, prenez par exemple `10.10.10.0/24`. Un LAN et un WAN dans le même sous-réseau cassent le routage.

### 1.2 Schéma de l'architecture (à reproduire proprement sur le compte-rendu)

```
                              INTERNET
                                  │
                   Réseau de l'établissement (WAN)
                                  │
 ┌────────────────────── Hôte Proxmox VE ──────────────────────────────┐
 │                                │                                    │
 │                  ══════ vmbr0 (bridge WAN, carte physique) ══════   │
 │                                │                                    │
 │                         ens18 (DHCP WAN, ex. 172.16.x.y)            │
 │                     ┌──────────┴──────────┐                         │
 │                     │  VM 101 r1-routeur  │  ip_forward = 1         │
 │                     │   NAT/PAT nftables  │  masquerade → ens18     │
 │                     └──────────┬──────────┘                         │
 │                         ens19  192.168.10.1  (passerelle)           │
 │                                │                                    │
 │  ════════ vmbr1 (bridge LAN ISOLÉ — aucun port physique, aucune IP hôte) ════════
 │       │                 │                  │                 │          │
 │  192.168.10.2      192.168.10.3      192.168.10.4     192.168.10.100-200│
 │ ┌──────────┐     ┌──────────────┐    ┌──────────┐     ┌─────────────┐   │
 │ │ VM 102   │     │ VM 103       │    │ VM 104   │     │ VM 105      │   │
 │ │ srv-dhcp │     │ srv-dns      │    │ srv-web  │     │ client      │   │
 │ │ isc-dhcp │     │ AdGuardHome  │    │ nginx    │     │ Firefox     │   │
 │ │ (ou Kea) │     │ forward +    │    │ app.pme. │     │ Wireshark   │   │
 │ │          │     │ rewrite      │    │ lan      │     │ (DHCP)      │   │
 │ └──────────┘     └──────────────┘    └──────────┘     └─────────────┘   │
 └─────────────────────────────────────────────────────────────────────────┘

 DHCP distribue :  IP 192.168.10.100-200 / passerelle 192.168.10.1 / DNS 192.168.10.3 / domaine pme.lan
 AdGuardHome    :  amont 1.1.1.1 + 9.9.9.9   |   réécriture  app.pme.lan → 192.168.10.4
```

### 1.3 Réponses aux trois questions de conception

**Q1 — Pourquoi les serveurs sont-ils en IP statique alors que le client est en DHCP ?**
Les serveurs sont des **points de référence** : d'autres équipements les désignent par leur adresse. Le DHCP distribue « passerelle = 192.168.10.1 » et « DNS = 192.168.10.3 », et la réécriture DNS pointe vers 192.168.10.4. Si ces adresses changeaient, toute la configuration deviendrait fausse. Le serveur DHCP **ne peut pas** non plus obtenir sa propre adresse par DHCP : c'est le problème de la poule et de l'œuf. Le client, lui, n'est joint par personne à une adresse précise. Le DHCP permet de le gérer **automatiquement et à grande échelle** (centaines de postes) sans erreur de saisie ni doublon d'IP.

**Q2 — Le serveur DHCP et le routeur sont sur le même segment : faut-il un relais DHCP ?**
**Non.** Un client sans adresse émet un **DHCPDISCOVER en broadcast** (`0.0.0.0 → 255.255.255.255`, MAC `ff:ff:ff:ff:ff:ff`). Ce broadcast est diffusé à tout le **domaine de diffusion** (`vmbr1`), où se trouve le serveur DHCP, qui le reçoit directement. Un **relais DHCP** (`ip helper-address`, `isc-dhcp-relay`) ne sert que si le serveur est **dans un autre sous-réseau**, car **un routeur ne transmet pas les broadcasts**. Le routeur n'intervient donc pas du tout dans l'échange DHCP.

**Q3 — Que mettez-vous dans l'option « serveur DNS » du DHCP, et pourquoi pas l'adresse du routeur ?**
On met **192.168.10.3**, l'adresse d'AdGuardHome (option 6 : `domain-name-servers`). Il ne faut pas mettre l'adresse du routeur, pour trois raisons :

1. Le routeur **n'héberge aucun service DNS** (rôles séparés, E1). Une requête sur le port 53 du routeur n'obtient aucune réponse.
2. L'exigence **E4** impose que **toute** la résolution passe par le résolveur interne. C'est ce qui permet de **journaliser** les requêtes (preuve demandée) et de **filtrer**.
3. Seul AdGuardHome connaît la **réécriture `app.pme.lan`**. Un autre DNS (celui du routeur, de la box ou de l'opérateur) répondrait **NXDOMAIN** pour ce nom fictif, et E6 échouerait.

On confond souvent **passerelle** (le routeur : par où sortent les paquets) et **serveur DNS** (qui traduit les noms). Ce sont deux fonctions distinctes, portées ici par deux machines distinctes.

---

## 2. Préparation de Proxmox

### 2.1 Créer le bridge LAN isolé `vmbr1` (équivalent de VMnet2)

**Interface web :** `Datacenter → <votre nœud> → System → Network → Create → Linux Bridge`

| Champ | Valeur |
|---|---|
| Name | `vmbr1` |
| IPv4/CIDR | **(vide)** |
| Gateway | **(vide)** |
| Bridge ports | **(vide)**, c'est ce qui garantit l'isolation |
| Autostart | ✔ |
| Comment | `LAN PME isole (equiv. VMnet2)` |

Cliquez ensuite sur **Apply Configuration**.

Résultat attendu dans `/etc/network/interfaces` de l'hôte :

```
auto vmbr1
iface vmbr1 inet manual
        bridge-ports none
        bridge-stp off
        bridge-fd 0
#LAN PME isole (equiv. VMnet2)
```

> **Proxmox partagé par plusieurs étudiants ?** Les bridges sont communs à tout le nœud. Prenez un nom unique (`vmbr1xx` avec votre numéro), ou demandez à l'enseignant une zone **SDN « Simple »** ou un **VLAN** dédié. Deux DHCP d'étudiants sur le même `vmbr1` = deux DHCP concurrents (§ 8 de l'énoncé).

**Vérifier l'isolation (preuve à montrer AVANT de lancer DHCP et DNS)**, sur le shell de l'hôte :

```bash
ip -br addr show vmbr1          # aucune adresse IPv4 -> l'hôte n'est pas sur le LAN
bridge link | grep vmbr1        # seules des interfaces tapXXXiY (VM) apparaissent, aucune carte physique (enoX, ethX)
grep -A4 "iface vmbr1" /etc/network/interfaces   # bridge-ports none
```

### 2.2 Option « fidèle à VMnet8 » (facultative)

L'énoncé met le WAN derrière un NAT VMware. Dans la configuration ci-dessus, le WAN du routeur est **directement sur le réseau de l'établissement** (`vmbr0`). C'est sans danger, car **seul le routeur** y est branché et il n'héberge ni DHCP ni DNS. Pour reproduire exactement VMnet8 (double NAT), créez un bridge NAT sur l'hôte :

```
# /etc/network/interfaces de l'hôte Proxmox (adapter vmbr0 si besoin)
auto vmbr8
iface vmbr8 inet static
        address 10.8.8.1/24
        bridge-ports none
        bridge-stp off
        bridge-fd 0
        post-up   echo 1 > /proc/sys/net/ipv4/ip_forward
        post-up   iptables -t nat -A POSTROUTING -s 10.8.8.0/24 -o vmbr0 -j MASQUERADE
        post-down iptables -t nat -D POSTROUTING -s 10.8.8.0/24 -o vmbr0 -j MASQUERADE
```

Le WAN du routeur passe alors sur `vmbr8`, en statique : `address 10.8.8.2/24`, `gateway 10.8.8.1`, DNS `1.1.1.1`. **Il faut des droits root sur l'hôte. Sur un Proxmox d'établissement, demandez l'accord avant.**

### 2.3 Récupérer l'ISO Debian

`local (stockage) → ISO Images → Download from URL` →
`https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/` (fichier `debian-13.x.y-amd64-netinst.iso`).

### 2.4 Créer le template Debian (une seule installation pour toutes les VM)

Shell de l'hôte (adaptez le nom de l'ISO et le stockage `local-lvm`) :

```bash
qm create 100 --name debian13-base --ostype l26 \
  --cores 1 --memory 1024 \
  --scsihw virtio-scsi-single --scsi0 local-lvm:20 \
  --net0 virtio,bridge=vmbr0,firewall=0 \
  --ide2 local:iso/debian-13.1.0-amd64-netinst.iso,media=cdrom \
  --boot 'order=scsi0;ide2' --agent 1
qm start 100
```

Pendant l'installation (console noVNC) :

- réseau en DHCP sur `vmbr0` (le template n'a **aucun service réseau**, il peut donc être sur le WAN) ;
- utilisateur `etudiant` + mot de passe root ;
- **logiciels :** décochez « environnement de bureau », cochez **« serveur SSH »** et **« utilitaires usuels du système »**.

Après le premier démarrage, dans la VM 100 :

```bash
apt update && apt full-upgrade -y
apt install -y qemu-guest-agent curl bind9-dnsutils tcpdump nftables conntrack sudo vim
usermod -aG sudo etudiant
# Rendre le template "clonable" : identifiant machine régénéré au 1er boot de chaque clone
truncate -s 0 /etc/machine-id
rm -f /var/lib/dbus/machine-id && ln -s /etc/machine-id /var/lib/dbus/machine-id
poweroff
```

Puis, sur l'hôte :

```bash
qm set 100 --ide2 none,media=cdrom
qm template 100
```

### 2.5 Créer les 5 VM par clonage

```bash
# Routeur : WAN sur vmbr0 + LAN sur vmbr1
qm clone 100 101 --name r1-routeur --full 1
qm set 101 --net0 virtio,bridge=vmbr0,firewall=0 --net1 virtio,bridge=vmbr1,firewall=0

# Serveurs : UNIQUEMENT sur vmbr1 (jamais sur vmbr0 !)
qm clone 100 102 --name srv-dhcp --full 1 && qm set 102 --net0 virtio,bridge=vmbr1,firewall=0
qm clone 100 103 --name srv-dns  --full 1 && qm set 103 --net0 virtio,bridge=vmbr1,firewall=0
qm clone 100 104 --name srv-web  --full 1 && qm set 104 --net0 virtio,bridge=vmbr1,firewall=0

# Client : plus de RAM pour le bureau graphique
qm clone 100 105 --name client   --full 1 && qm set 105 --memory 4096 --cores 2 --vga std
```

**Sur chaque clone, au premier démarrage** (console noVNC), remplacez `NOM` par `r1-routeur`, `srv-dhcp`… :

```bash
hostnamectl set-hostname NOM
sed -i "s/debian13-base/NOM/g" /etc/hosts
rm -f /etc/ssh/ssh_host_* && dpkg-reconfigure openssh-server   # nouvelles clés SSH
```

**Cas du client (VM 105).** Comme il n'héberge **aucun service**, on peut l'équiper pendant qu'il est encore sur `vmbr0`, puis le basculer :

```bash
apt install -y task-xfce-desktop firefox-esr wireshark   # répondre "Oui" : non-root peut capturer
usermod -aG wireshark etudiant
# Laisser NetworkManager gérer la carte : commenter ens18 dans /etc/network/interfaces
sed -i -E 's/^(auto|allow-hotplug|iface) ens18/#&/' /etc/network/interfaces
poweroff
```

Ensuite, dans Proxmox : `105 → Hardware → Network Device (net0) → Edit → Bridge : vmbr1`. La MAC est conservée.

> 🔒 **Règle de sécurité** : le serveur DHCP et AdGuardHome ne sont **jamais** installés ni démarrés sur une VM connectée à `vmbr0`. Contrôle : `qm config 102 | grep net` et `qm config 103 | grep net` doivent n'afficher que `bridge=vmbr1`.

---

## 3. PHASE A — Mettre les postes sur Internet

### Mission 2 — Le routeur (VM 101)

**`/etc/network/interfaces`**

```
# Boucle locale
auto lo
iface lo inet loopback

# WAN : vers vmbr0 (réseau de l'établissement -> Internet). Adresse obtenue en DHCP.
allow-hotplug ens18
iface ens18 inet dhcp

# LAN : vers vmbr1 (réseau PME isolé). Le routeur est la passerelle 192.168.10.1.
# Pas de "gateway" ici : la route par défaut vient du WAN.
auto ens19
iface ens19 inet static
    address 192.168.10.1/24
```

**Activer le routage IPv4** : `/etc/sysctl.d/99-routage.conf`

```
# Autorise le noyau à faire passer des paquets d'une interface à l'autre (fonction routeur)
net.ipv4.ip_forward = 1
```

**NAT/PAT + filtrage** : `/etc/nftables.conf`

```
#!/usr/sbin/nft -f
flush ruleset

define WAN     = "ens18"
define LAN     = "ens19"
define LAN_NET = 192.168.10.0/24

table inet filtre {
    chain input {                     # trafic destiné AU routeur lui-même
        type filter hook input priority filter; policy accept;
    }
    chain forward {                   # trafic qui TRAVERSE le routeur
        type filter hook forward priority filter; policy drop;
        ct state established,related accept               # les réponses d'Internet reviennent vers le LAN
        iifname $LAN oifname $WAN ip saddr $LAN_NET accept # le LAN peut sortir vers Internet
    }
    chain output {
        type filter hook output priority filter; policy accept;
    }
}

table ip nat {
    chain postrouting {
        type nat hook postrouting priority srcnat; policy accept;
        # NAT/PAT (masquerade) : tout paquet du LAN sortant par le WAN prend l'IP WAN du routeur
        # comme adresse source. Le port source peut être réécrit (PAT) pour distinguer les flux.
        # La table conntrack mémorise la correspondance pour retraduire les réponses.
        oifname $WAN ip saddr $LAN_NET masquerade
    }
}
```

Appliquer :

```bash
sysctl --system
systemctl enable --now nftables
nft -f /etc/nftables.conf
systemctl restart networking
```

**Ce qu'il faut savoir expliquer**

- **`ip_forward`** : sans lui, Linux jette les paquets qui ne lui sont pas destinés. La machine n'est alors pas un routeur.
- **`masquerade`** = SNAT dynamique. L'adresse privée `192.168.10.x` est **non routable sur Internet**, donc on la remplace par l'IP WAN. C'est du **PAT** parce que **plusieurs clients partagent une seule IP publique**, et le **port source** permet de distinguer leurs connexions.
- **`ct state established,related accept`** : le pare-feu est **à états**. Seules les réponses à des connexions initiées depuis le LAN peuvent entrer.

**Preuves à l'écran**

```bash
ip -br a                         # ens18 = IP WAN, ens19 = 192.168.10.1/24
ip route                         # default via <passerelle établissement> dev ens18
sysctl net.ipv4.ip_forward       # = 1
nft list ruleset                 # règle masquerade présente
ping -c3 1.1.1.1                 # le routeur sort sur Internet (couche IP)
ping -c3 deb.debian.org          # ... avec résolution de noms
curl -sI https://www.youtube.com | head -1   # HTTP/2 200 (couche application)
```

> Les serveurs (VM 102, 103, 104) ont besoin de cette mission terminée pour faire `apt install`.

---

### Mission 3 — Le serveur DHCP dédié (VM 102)

**Réseau statique** : `/etc/network/interfaces`

```
auto lo
iface lo inet loopback

auto ens18
iface ens18 inet static
    address 192.168.10.2/24
    gateway 192.168.10.1
```

`/etc/resolv.conf` (temporaire, tant qu'AdGuardHome n'existe pas) :

```
nameserver 1.1.1.1
```

```bash
systemctl restart networking
ping -c2 192.168.10.1 && ping -c2 deb.debian.org   # sort bien par le routeur
apt update && apt install -y isc-dhcp-server
```

> Si `isc-dhcp-server` n'est pas disponible dans votre version de Debian, utilisez **Kea**, son successeur chez ISC. Voir l'encadré plus bas.

**`/etc/default/isc-dhcp-server`** : on n'écoute **que** sur l'interface LAN.

```
INTERFACESv4="ens18"
INTERFACESv6=""
```

**`/etc/dhcp/dhcpd.conf`**

```
# Ce serveur fait autorité sur ce segment : il répond DHCPNAK aux baux invalides
authoritative;

# Durée des baux : 1 h par défaut, 2 h maximum
default-lease-time 3600;
max-lease-time 7200;

# Options globales envoyées au client
option domain-name "pme.lan";               # suffixe DNS -> "app" sera complété en "app.pme.lan"
option domain-name-servers 192.168.10.3;    # option 6 : DNS = AdGuardHome (PAS le routeur)

subnet 192.168.10.0 netmask 255.255.255.0 {
    range 192.168.10.100 192.168.10.200;    # plage dynamique (hors IP statiques .1-.49)
    option routers 192.168.10.1;            # option 3 : passerelle par défaut = le routeur
    option subnet-mask 255.255.255.0;       # option 1
    option broadcast-address 192.168.10.255;
}
```

```bash
dhcpd -t -cf /etc/dhcp/dhcpd.conf          # test de syntaxe
systemctl restart isc-dhcp-server
systemctl status isc-dhcp-server --no-pager
```

<details>
<summary><b>Alternative Kea</b> : <code>/etc/kea/kea-dhcp4.conf</code></summary>

```json
{
  "Dhcp4": {
    "interfaces-config": { "interfaces": [ "ens18" ] },
    "lease-database": { "type": "memfile", "persist": true },
    "valid-lifetime": 3600,
    "authoritative": true,
    "subnet4": [
      {
        "id": 1,
        "subnet": "192.168.10.0/24",
        "pools": [ { "pool": "192.168.10.100 - 192.168.10.200" } ],
        "option-data": [
          { "name": "routers",             "data": "192.168.10.1" },
          { "name": "domain-name-servers", "data": "192.168.10.3" },
          { "name": "domain-name",         "data": "pme.lan" }
        ]
      }
    ]
  }
}
```

Commandes : `apt install kea-dhcp4-server`, `kea-dhcp4 -t /etc/kea/kea-dhcp4.conf`, puis `systemctl restart kea-dhcp4-server`.
</details>

**Preuves à l'écran**

Côté **client** (VM 105) :

```bash
sudo nmcli device disconnect ens18 && sudo nmcli device connect ens18   # nouvelle demande DHCP
ip -br addr show ens18            # 192.168.10.1xx/24
ip route                          # default via 192.168.10.1
nmcli device show ens18 | grep -E 'IP4.(ADDRESS|GATEWAY|DNS|DOMAIN)'
cat /etc/resolv.conf              # nameserver 192.168.10.3 / search pme.lan
```

Côté **serveur DHCP** :

```bash
journalctl -u isc-dhcp-server -n 20 --no-pager   # DHCPDISCOVER -> OFFER -> REQUEST -> ACK
cat /var/lib/dhcp/dhcpd.leases                   # bail attribué (IP <-> MAC du client)
```

---

### Mission 4 — Le résolveur AdGuardHome et la navigation (VM 103)

**Réseau statique** : comme pour la VM 102, avec `address 192.168.10.3/24` et `gateway 192.168.10.1`. Mettez temporairement `nameserver 1.1.1.1` dans `/etc/resolv.conf`.

**Installation** (script officiel AdGuard) :

```bash
curl -s -S -L https://raw.githubusercontent.com/AdguardTeam/AdGuardHome/master/scripts/install.sh | sh -s -- -v
systemctl status AdGuardHome --no-pager
ss -lntup | grep -E ':53|:3000'   # le port 53 doit être libre ou tenu par AdGuardHome
```

**Assistant de configuration.** Depuis le **navigateur du client**, ouvrez `http://192.168.10.3:3000` (l'IP suffit, aucun DNS n'est encore nécessaire) :

| Étape | Choix |
|---|---|
| Interface web d'administration | Toutes les interfaces, port **80** |
| Serveur DNS | Toutes les interfaces (ou `192.168.10.3`), port **53** |
| Compte | `admin` + mot de passe robuste |

**Configurer les DNS amont** : `Paramètres → Paramètres DNS → Serveurs DNS amont`

```
1.1.1.1
9.9.9.9
```

Choisissez ensuite **Appliquer**, puis **Tester les DNS amont**.

> Si l'établissement bloque le port 53 sortant, utilisez le DNS de l'établissement (celui reçu par le WAN du routeur : `cat /etc/resolv.conf` sur la VM 101), ou du DoH : `https://dns.cloudflare.com/dns-query`.

Le serveur DNS utilise ensuite **son propre résolveur** (E4). Dans `/etc/resolv.conf` de la VM 103 :

```
nameserver 127.0.0.1
```

Sur les **VM 101 (côté LAN), 102 et 104**, remplacez aussi `1.1.1.1` par `nameserver 192.168.10.3`.

**Firefox côté client (important pour E4).** Désactivez le DNS-over-HTTPS de Firefox, sinon le navigateur **contourne** AdGuardHome : `Paramètres → Vie privée et sécurité → DNS via HTTPS → Désactivé` (ou `about:config` → `network.trr.mode = 5`).

**Preuves à l'écran** (client) :

```bash
dig youtube.com                    # ";; SERVER: 192.168.10.3#53" -> c'est bien AdGuard qui répond
curl -sI https://www.youtube.com | head -1
```

Ouvrez ensuite `https://www.youtube.com` dans Firefox, puis, dans AdGuardHome, **`Journal des requêtes`** : la ligne `youtube.com` / client `192.168.10.1xx` / « Traité par 1.1.1.1 » apparaît. **Faites une capture d'écran : c'est un livrable.**

✅ **Fin de Phase A** : le client est en DHCP, utilise AdGuard comme DNS, sort par le routeur NAT, et les quatre rôles sont sur quatre machines.

---

## 4. PHASE B — Publier l'application interne par son nom

### Mission 5 — Le serveur web on-premise (VM 104)

Réseau statique : `address 192.168.10.4/24`, `gateway 192.168.10.1`, `nameserver 192.168.10.3`.

```bash
apt install -y nginx
cat > /var/www/html/index.html <<'EOF'
<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Intranet PME</title></head>
<body style="font-family:sans-serif;text-align:center;margin-top:10%">
  <h1>Application interne PME</h1>
  <p>Servie par <b>srv-web</b> — 192.168.10.4 — hébergement on-premise</p>
</body></html>
EOF
systemctl enable --now nginx
ss -lntp | grep ':80'
```

**Preuve « joignable uniquement par l'IP »** (client) :

```bash
curl http://192.168.10.4          # la page s'affiche
dig app.pme.lan                    # status: NXDOMAIN -> le nom n'existe pas encore
curl http://app.pme.lan            # "Could not resolve host"
```

Faites la même vérification dans Firefox : `http://192.168.10.4` fonctionne, `http://app.pme.lan` échoue.

### Mission 6 — La publication par le nom (AdGuardHome)

**Interface web d'AdGuardHome :** `Filtres → Réécritures DNS → Ajouter une réécriture DNS`

| Domaine | Réponse |
|---|---|
| `app.pme.lan` | `192.168.10.4` |

Équivalent dans `/opt/AdGuardHome/AdGuardHome.yaml` (arrêtez le service avant d'éditer : `systemctl stop AdGuardHome`). L'emplacement exact varie selon la version : sur les versions récentes, la clé `rewrites` est sous `filtering:` et chaque entrée peut porter `enabled: true`.

```yaml
filtering:
  rewrites:
    - domain: app.pme.lan        # nom demandé par le client
      answer: 192.168.10.4      # AdGuard répond lui-même avec cette IP, sans interroger l'amont
```

**Double validation (E7).** Petit script de démonstration côté client, `~/verif.sh` :

```bash
#!/bin/bash
echo "== DNS interne ==";  dig +short app.pme.lan
echo "== DNS externe ==";  dig +short youtube.com | head -2
echo "== HTTP interne =="; curl -s -o /dev/null -w "%{http_code} %{remote_ip}\n" http://app.pme.lan
echo "== HTTP externe =="; curl -s -o /dev/null -w "%{http_code} %{remote_ip}\n" https://www.youtube.com
```

Résultat attendu : `192.168.10.4`, une IP publique, `200 192.168.10.4`, puis `200 <IP publique>`.

Ouvrez ensuite **deux onglets Firefox côte à côte** : `http://app.pme.lan` et `https://www.youtube.com`. Prenez une capture d'écran, puis une autre du **journal AdGuard** montrant les deux requêtes : `app.pme.lan` « Réécrit » et `youtube.com` « Traité ».

> Astuce : grâce à `option domain-name "pme.lan"`, `http://app/` fonctionne aussi. Le client ajoute le suffixe de recherche. Tapez toujours `http://` devant, sinon Firefox lance une recherche web.

**À savoir expliquer : AdGuardHome ne détient pas de zone `pme.lan`.**

```bash
dig app.pme.lan @192.168.10.3      # 192.168.10.4 : réponse fabriquée par la règle de réécriture
dig autre.pme.lan @192.168.10.3    # NXDOMAIN, et dans le journal, "Traité par 1.1.1.1" :
                                   # le nom n'a pas de règle, il est transféré à l'amont,
                                   # et la racine répond que ".lan" n'existe pas
dig SOA pme.lan @192.168.10.3      # pas de SOA "à vous" : aucune zone n'est hébergée
```

---

## 5. PHASE C — Mission 7 : mesure et analyse avec Wireshark

### 5.1 Capture côté client (trajet complet)

1. Sur le client, lancez **Wireshark** et démarrez la capture sur **`ens18`**.
2. Dans un terminal, repartez d'un poste « propre » :

   ```bash
   sudo nmcli device disconnect ens18     # libère le bail (DHCPRELEASE)
   sudo ip neigh flush all                # vide le cache ARP
   ip neigh                               # vérification : vide
   sudo nmcli device connect ens18        # nouvelle obtention DHCP : DISCOVER/OFFER/REQUEST/ACK
   ```

3. Dans Firefox, en **fenêtre privée** (pas de cache, donc un vrai `200 OK` et non un `304`), ouvrez `http://app.pme.lan`, puis `https://www.youtube.com`.
4. Arrêtez la capture et enregistrez-la : `Fichier → Enregistrer sous → tp-pme.pcapng`.

Filtre d'affichage utile :

```
dhcp || arp || dns || (ip.addr == 192.168.10.4 && tcp.port == 80)
```

### 5.2 Capture côté WAN du routeur (preuve du NAT/PAT)

La capture du client ne voit **que** le côté LAN. Pour **prouver le NAT**, il faut voir le **même flux des deux côtés du routeur**. Sur l'**hôte Proxmox**, les interfaces des VM s'appellent `tap<VMID>i<n°carte>` :

```bash
# net0 du routeur = WAN = tap101i0 ; net1 = LAN = tap101i1
tcpdump -i tap101i1 -w /root/nat-lan.pcapng  host 1.1.1.1 or port 443 &
tcpdump -i tap101i0 -w /root/nat-wan.pcapng  host 1.1.1.1 or port 443 &
# ... générer du trafic depuis le client (dig, youtube) ... puis :
kill %1 %2
# Récupérer les fichiers sur votre PC : scp root@<IP-proxmox>:/root/nat-*.pcapng .
```

Sans accès à l'hôte, lancez directement sur le routeur `tcpdump -i ens18 -w nat-wan.pcapng` et `tcpdump -i ens19 -w nat-lan.pcapng`.

Vous pouvez aussi montrer la table de traduction du routeur :

```bash
conntrack -L | grep 192.168.10.
# ex : tcp ... src=192.168.10.100 dst=142.250.x.x sport=51234 dport=443
#              src=142.250.x.x dst=<IP_WAN> sport=443 dport=51234  [ASSURED]
#   -> aller : source privée ; retour : vers l'IP WAN du routeur = traduction NAT/PAT
```

### 5.3 Modèle d'annotation à rendre (à remplir avec VOS numéros de paquets)

| N° paquet | Protocole | Source → Destination | Étape et explication |
|---|---|---|---|
| … | DHCP Release | 192.168.10.1xx → 192.168.10.2 | Libération de l'ancien bail |
| … | DHCP Discover | 0.0.0.0 → 255.255.255.255 | Le client sans IP cherche un serveur DHCP (**broadcast**, d'où l'absence de relais) |
| … | ICMP Echo (facultatif) | 192.168.10.2 → IP proposée | isc-dhcpd vérifie que l'IP est libre avant de la proposer |
| … | DHCP Offer | 192.168.10.2 → client | Proposition : IP + options 1, 3 (routeur), 6 (DNS), 15 (domaine) |
| … | DHCP Request | 0.0.0.0 → 255.255.255.255 | Le client accepte l'offre |
| … | DHCP ACK | 192.168.10.2 → client | Bail confirmé : le client configure IP, passerelle et DNS |
| … | ARP (probe / gratuitous) | client | Le client vérifie que personne d'autre n'a son IP |
| … | ARP Request / Reply | « Who has 192.168.10.3? » | Pour envoyer sa requête DNS, le client cherche la MAC du **résolveur** (même réseau) |
| … | DNS Query / Response | client ↔ 192.168.10.3 | `A app.pme.lan` → `192.168.10.4` (réécriture AdGuard) |
| … | ARP Request / Reply | « Who has 192.168.10.4? » | Le serveur web est **local** : le client cherche **sa** MAC |
| … | TCP SYN, SYN/ACK, ACK | client ↔ 192.168.10.4:80 | Poignée de main TCP en 3 temps |
| … | HTTP GET / | client → 192.168.10.4 | Requête de la page (`Host: app.pme.lan`) |
| … | HTTP 200 OK | 192.168.10.4 → client | La page est servie |
| … | DNS Query / Response | client ↔ 192.168.10.3 | `A www.youtube.com` → IP publique (transférée à l'amont) |
| … | ARP Request / Reply | « Who has 192.168.10.1? » | YouTube est **distant** : le client cherche la MAC de la **passerelle** |
| … | TCP SYN → IP YouTube :443 | client → IP publique | La trame Ethernet porte la **MAC du routeur**, mais le paquet IP porte l'**IP de YouTube** |

Dans Wireshark, faites `Clic droit sur un paquet → Packet Comment` pour annoter directement dans le `.pcapng`, en plus du tableau.

### 5.4 Analyse ARP : local et distant

Le client fait un **ET logique** entre l'IP de destination et son masque /24 :

- `192.168.10.4` est **dans** `192.168.10.0/24`. C'est une **livraison directe** : le client émet `ARP Who has 192.168.10.4?`, et la trame part directement à la MAC du serveur web. **Le routeur n'est pas traversé.**
- L'IP de YouTube est **hors** du réseau, donc le client consulte sa table de routage : `default via 192.168.10.1`. C'est une **livraison indirecte** : il émet `ARP Who has 192.168.10.1?` et envoie la trame à la **MAC du routeur**, avec **l'IP de YouTube** dans l'en-tête IP. L'ARP ne fonctionne **que dans le domaine de diffusion local**. On ne peut jamais obtenir la MAC d'un serveur YouTube.

---

## 6. Préparation de la soutenance : réponses aux 5 questions

**1. Pourquoi le client cherche-t-il la MAC du serveur web pour `app.pme.lan`, mais celle de la passerelle pour YouTube ?**
Voir le § 5.4. `192.168.10.4` est sur le même sous-réseau (même /24), donc la livraison est directe et le client fait un ARP sur la cible. YouTube est hors sous-réseau, donc la livraison passe par la route par défaut et le client fait un ARP sur le **next-hop** 192.168.10.1. Les adresses IP restent de bout en bout. Les adresses MAC changent à chaque saut.

**2. Le DHCP a-t-il résolu `app.pme.lan` ?**
**Non.** Le DHCP n'a fait que **configurer** le client : IP, masque, passerelle, **adresse du DNS (option 6)** et suffixe `pme.lan`. La résolution est faite **plus tard, par AdGuardHome** (192.168.10.3), grâce à une **règle de réécriture DNS**. Le client envoie `A? app.pme.lan` en UDP/53, et AdGuard répond lui-même `192.168.10.4` **sans interroger l'amont**. On le voit dans le journal (« Réécrit ») et dans Wireshark (paquets DNS entre le client et .3).

**3. Quelle différence entre AdGuardHome (forwarder + réécriture) et bind9 (autoritaire) ?**

| | bind9 autoritaire | AdGuardHome |
|---|---|---|
| Rôle | **Détient** une zone (fichier de zone) et fait **foi** pour celle-ci | **Relaie** les requêtes des clients vers un DNS amont (forwarder) |
| Données | SOA, NS, A, MX… : la zone **complète** | Pas de zone, seulement des **règles** de réécriture (nom → IP) |
| Réponse | Flag **AA** (Authoritative Answer) | Réponse **fabriquée** localement pour le nom réécrit, transférée à l'amont pour tout le reste |
| Nom absent | NXDOMAIN **avec SOA de la zone** | Transféré à l'amont, puis NXDOMAIN venant de la racine |
| Usage | Publier un domaine | Résolveur des postes : cache, filtrage, journal, surcharge locale |

Une réécriture est une **surcharge ponctuelle d'un nom**, pas une délégation ni une zone. Preuve : `dig autre.pme.lan @192.168.10.3` renvoie NXDOMAIN venu de l'amont.

**4. Montrez dans la capture le paquet qui prouve le NAT/PAT.**
Ouvrez `nat-lan.pcapng` et `nat-wan.pcapng` (§ 5.2), et repérez **le même SYN** vers YouTube :

- côté LAN : `src 192.168.10.1xx:51234 → dst 142.250.x.x:443` ;
- côté WAN : `src <IP_WAN_routeur>:51234 (ou un autre port) → dst 142.250.x.x:443`.

L'IP source a été remplacée (**NAT**) et le port sert d'identifiant de session (**PAT**). La réponse revient vers l'IP WAN, et le routeur la retraduit vers le client grâce à `conntrack`. La capture du client seule **ne peut pas** prouver le NAT, puisqu'elle ne voit que des adresses privées.

**5. Si on arrête le serveur web en gardant la réécriture : que répond le DNS ? Et le navigateur ?**
- **DNS** : il répond toujours `app.pme.lan → 192.168.10.4`. AdGuard applique une règle statique et **ne vérifie pas** que le service est vivant. Le DNS est un **annuaire**, pas une sonde.
- **Navigateur** : il affiche une **erreur**, pour une raison qui dépend de ce qui est arrêté :
  - **VM éteinte** : l'ARP `Who has 192.168.10.4?` reste sans réponse et le SYN n'est jamais envoyé. On obtient « délai dépassé » ou « No route to host ».
  - **nginx seul arrêté** : l'ARP répond et le SYN arrive, mais le noyau du serveur renvoie un **TCP RST** car aucun processus n'écoute sur le port 80. On obtient « La connexion a échoué » (*connection refused*).
- **Pourquoi cette différence** : la résolution de noms (couche application, DNS) et la disponibilité du service (couches 2 à 4 et 7 vers le serveur) sont **indépendantes**. Un nom résolu ne garantit pas un service joignable.

---

## 7. Livrables : checklist

- [ ] **Schéma + plan d'adressage + réponses Q1, Q2, Q3** (§ 1). C'est obligatoire et doit être validé par l'enseignant avant toute construction.
- [ ] Configurations commentées : `/etc/network/interfaces` et `/etc/nftables.conf` du routeur, `/etc/sysctl.d/99-routage.conf`, `/etc/dhcp/dhcpd.conf` et `/etc/default/isc-dhcp-server`, la réécriture AdGuard (capture d'écran ou extrait YAML).
- [ ] Captures du journal AdGuard : une requête **externe** (`youtube.com`, « Traité ») et une requête **interne** (`app.pme.lan`, « Réécrit »).
- [ ] Preuve de la double validation : sortie de `verif.sh` et capture des deux onglets.
- [ ] `tp-pme.pcapng` **avec le tableau d'annotation rempli** (§ 5.3), plus `nat-lan.pcapng` et `nat-wan.pcapng` pour le NAT.
- [ ] Note « usage de l'IA » (modèle ci-dessous).

### Modèle de note « Usage de l'IA »

> **Outil utilisé :** assistant IA conversationnel (Claude).
> **Où il m'a servi :**
> 1. Adaptation de l'énoncé VMware à Proxmox VE (bridge isolé `vmbr1` au lieu de VMnet2, template et clones). Ma demande : « adapte ce TP VMware pour Proxmox ».
> 2. Génération des configurations de base : nftables (NAT/PAT), `dhcpd.conf`, réécriture AdGuardHome.
> 3. *(à compléter : débogage éventuel, avec le message d'erreur et la solution)*
>
> **Ce que j'ai vérifié et compris moi-même :** *(expliquez en vos mots la règle `masquerade`, l'option 6 du DHCP, la différence entre réécriture et zone autoritaire)*.

---

## 8. Dépannage rapide

| Symptôme | Cause probable | Vérification / correction |
|---|---|---|
| Le client n'obtient pas d'IP | DHCP arrêté, mauvaise interface, ou client pas sur `vmbr1` | `systemctl status isc-dhcp-server`, `INTERFACESv4`, `qm config 105 \| grep net0` |
| Le client a une IP mais aucun ping vers 1.1.1.1 | `ip_forward=0`, NAT absent, ou réseau LAN = réseau WAN | Sur le routeur : `sysctl net.ipv4.ip_forward`, `nft list ruleset`, `ip route` |
| Le ping vers 1.1.1.1 passe, mais pas `youtube.com` | Problème DNS | `dig youtube.com @192.168.10.3`, DNS amont d'AdGuard, port 53 sortant bloqué ? |
| AdGuard ne démarre pas sur le port 53 | Port déjà pris | `ss -lntup \| grep :53` (systemd-resolved, dnsmasq…) |
| `app.pme.lan` fonctionne avec `dig` mais pas dans Firefox | DoH de Firefox actif ou cache | Désactiver le DoH, `about:networking#dns`, fenêtre privée |
| Pas de trace dans le journal AdGuard | Le client n'interroge pas .3 | `cat /etc/resolv.conf` sur le client, option 6 du DHCP |
| Deux clones ont la même IP en DHCP | `machine-id` identique | `truncate -s0 /etc/machine-id`, reboot (§ 2.4) |
