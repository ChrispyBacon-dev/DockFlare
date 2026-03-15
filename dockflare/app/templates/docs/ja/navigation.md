# DockFlare ドキュメントへようこそ!

DockFlare は、Cloudflare Tunnel と Zero Trust の管理を簡素化する自己ホスト型の入口コントローラーです。Docker ラベルによる自動構成に加え、手動のサービス定義やポリシー上書きのための堅牢な管理画面も提供します。

このドキュメントでは、DockFlare に関する情報を幅広く提供します。初めての方も、既に運用している方も、DockFlare を最大限に活用するための要点を見つけられます。

## 目次

* **[ホーム](Home.md)**
* **はじめに**
    * [前提条件](Prerequisites.md)
    * [クイックスタート (Docker Compose)](Quick-Start-Docker-Compose.md)
    * [管理画面へのアクセス](Accessing-the-Web-UI.md)
* **コアコンセプト**
    * [DockFlare の仕組み](How-DockFlare-Works.md)
    * [DockFlare Agent とマルチサーバーアーキテクチャ](Multi-Server-Agent.md)
    * [アクセスポリシーのベストプラクティス](Access-Policy-Best-Practices.md)
    * [ゾーンのデフォルトポリシー](Zone-Default-Policies.md)
    * [内部 vs 外部 `cloudflared`](Internal-vs-External-cloudflared.md)
    * [状態永続性](State-Persistence.md)
* **構成**
    * [コンテナラベル](Container-Labels.md)
    * [アイデンティティプロバイダー](Identity-Providers.md)
    * [OAuth プロバイダーのセットアップ](OAuth-Provider-Setup.md)
* **使用ガイド**
    * [基本的な使い方 (単一ドメイン)](Basic-Usage-Single-Domain.md)
    * [複数のドメインの使用 (インデックス付きラベル)](Using-Multiple-Domains-Indexed-Labels.md)
    * [ワイルドカードドメインの使用](Using-Wildcard-Domains.md)
    * [DNS ゾーンの管理](Managing-DNS-Zones.md)
    * [Graceful Deletion を理解する](Understanding-Graceful-Deletion.md)
    * [管理画面の使い方](Using-the-Web-UI.md)
    * [バックアップと復元](Backup-and-Restore.md)
* **高度なトピック**
    * [外部 `cloudflared` モード](External-cloudflared-Mode.md)
    * [モードの切り替え](Switching-Between-Modes.md)
    * [Prometheus と Grafana によるモニタリング](Monitoring-with-Prometheus-&-Grafana.md)
    * [パフォーマンスチューニング](Performance-Tuning.md)
    * [コンテンツセキュリティポリシー (CSP)](Content-Security-Policy.md)
    * [セキュリティアーキテクチャと強化](Security-Architecture.md)
* **トラブルシューティング**
    * [一般的な問題](Common-Issues.md)
    * [デバッグとログ](Debugging-&-Logs.md)
    * [ヘルスチェック](Health-Checks.md)
    * [CLI ユーティリティ](CLI-Utilities.md)
* **[寄稿](Contributing.md)**
* **[ライセンス](License.md)**
