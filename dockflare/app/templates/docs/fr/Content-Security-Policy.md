# Politique de sécurité du contenu (CSP)

## Qu'est-ce qu'une politique de sécurité du contenu ?

Une politique de sécurité du contenu (CSP) est une norme de sécurité Web qui permet de prévenir certains types d'attaques, notamment les attaques de type Cross-Site Scripting (XSS) et les attaques par injection de données. Il fonctionne en indiquant au navigateur quelles sources de contenu (scripts, styles, images, etc.) sont fiables et autorisées à être chargées sur une page Web.

## CSP de DockFlare

L'application DockFlare elle-même dispose d'une interface web. Pour protéger cette interface et assurer sa sécurité, DockFlare met en œuvre une politique de sécurité de contenu stricte sur sa propre interface utilisateur.

Il s'agit d'une fonctionnalité de sécurité interne importante conçue pour vous protéger, en tant qu'administrateur, contre les vulnérabilités potentielles basées sur le navigateur lorsque vous utilisez le tableau de bord DockFlare.

## Portée du CSP

Il est important de comprendre que le CSP de DockFlare s'applique **uniquement à l'interface web de DockFlare elle-même**.

Il n'affecte **pas**, ne modifie pas ou n'ajoute aucun en-tête CSP au trafic transmis via votre tunnel Cloudflare vers vos propres applications. Si vous souhaitez implémenter un CSP sur vos propres applications, vous devez le configurer dans les applications elles-mêmes (par exemple, en définissant l'en-tête HTTP `Content-Security-Policy` dans votre serveur Web ou le code de votre application).

##Configuration

Le CSP de DockFlare fait partie intégrante de sa posture de sécurité et n'est **pas configurable par l'utilisateur**. La politique est soigneusement conçue pour être aussi restrictive que possible tout en permettant à l'interface utilisateur de fonctionner correctement.

Si vous souhaitez en savoir plus sur le fonctionnement général des politiques de sécurité du contenu, les [MDN Web Docs on CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) sont une excellente ressource.
