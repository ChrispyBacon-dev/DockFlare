## OAuth プロバイダーのセットアップ

> **📌 重要:** このガイドは、**DockFlare 管理画面の認証**を設定するためのものです。サービスを保護するために **Cloudflare Access ポリシー** 用の OAuth/OIDC を構成したい場合は、代わりに [アイデンティティプロバイダー](Identity-Providers.md) を参照してください。

DockFlare では、OpenID Connect（OIDC）標準を使ってユーザー認証を外部プロバイダーに委任できます。これにより、DockFlare の Web インターフェースでシングルサインオン（SSO）を利用でき、Google、Authentik、Okta などの ID プロバイダーと連携できます。

### 新しいプロバイダーを追加する

新しい OIDC プロバイダーを追加するには、次の手順に従ってください。

1. **設定ページを開く:** メインダッシュボードから **設定** ページに移動します。
2. **OAuth セクションを探す:** **OAuth Authentication** セクションまでスクロールします。
3. **プロバイダーを追加する:** **プロバイダーの追加** ボタンをクリックして、設定モーダルを開きます。

表示される項目は次のとおりです。

* **プロバイダーの種類:** これは `OpenID Connect (OIDC)` に設定されています。フェデレーション認証の現在の標準です。
* **発行者 URL:** 最も重要な項目です。OIDC プロバイダーのベース URL であり、DockFlare はこれを使ってプロバイダー設定を自動検出します。たとえば `https://accounts.google.com` や `https://authentik.yourdomain.com/application/o/dockflare/` です。
* **プロバイダー ID:** このプロバイダー用の短く一意な小文字の名前です。例: `google`、`authentik-corp`。この ID は内部処理やコールバック URL に使われます。
* **表示名:** ログインボタンに表示される、わかりやすい名前です。例: `Google`、`Corporate SSO`。
* **クライアント ID:** DockFlare アプリケーションの公開識別子で、OIDC プロバイダーの開発者コンソールから取得します。
* **クライアント シークレット:** DockFlare アプリケーション用のシークレットで、こちらもプロバイダーのコンソールから取得します。
* **プロバイダーを有効にする:** このチェックボックスで、プロバイダーをいつでも有効化または無効化できます。

入力が完了したら、**プロバイダーの追加** をクリックして保存します。

### コールバック URL を確認する

プロバイダーを追加すると、必要な **コールバック URL** が設定ページのプロバイダー項目の下に表示されます。これは「承認済みリダイレクト URI」とも呼ばれます。

この URL をそのままコピーし、プロバイダーの管理コンソールで許可されたコールバック URL の一覧に追加してください。

---

### 例: Google を設定する

ここでは、Google を OAuth プロバイダーとして設定する簡単な流れを示します。

1. **Google Cloud Console を開く:** [API とサービス > 認証情報](https://console.cloud.google.com/apis/credentials) ページに移動します。
2. **認証情報を作成する:** **+ 認証情報を作成** をクリックし、**OAuth クライアント ID** を選択します。
3. **アプリケーションを設定する:**
   * **アプリケーション タイプ**を **Web アプリケーション** に設定します。
   * 任意の名前を付けます。たとえば `DockFlare` です。
4. **リダイレクト URI を追加する:**
   * **承認されたリダイレクト URI** の下で **+ URI の追加** をクリックします。
   * DockFlare が表示するコールバック URL を入力します。例: `https://your-dockflare-domain.com/auth/google/callback`
5. **作成してコピーする:** **作成** をクリックすると、**クライアント ID** と **クライアント シークレット** が表示されます。これらをコピーしてください。
6. **DockFlare で設定する:**
   * **発行者 URL:** `https://accounts.google.com`
   * **プロバイダー ID:** `google`
   * **表示名:** `Google`
   * **クライアント ID:** `(Your Client ID from Google)`
   * **クライアント シークレット:** `(Your Client Secret from Google)`

DockFlare にこのプロバイダーを保存すると、Google アカウントでログインできるようになります。

---

### OAuth と Access ポリシーを使って DockFlare を構成する

OAuth 認証を使う場合は、メインの DockFlare インターフェースを Access ポリシーで保護しつつ、OAuth コールバックが正しく動作するように構成したいことがあります。特に、DockFlare インスタンスに IP 制限やその他のアクセス制御がある場合は重要です。

#### **ベストプラクティス: OAuth コールバック用の bypass ポリシー**

インデックス付きラベルを使って、メインインターフェース用と OAuth コールバックパス用に別々のルールを定義します。

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    labels:
      # Main DockFlare interface with access policy
      - "dockflare.enable=true"
      - "dockflare.hostname=dockflare.example.com"
      - "dockflare.service=http://dockflare:5000"
      - "dockflare.access.group=team"  # your custom access policy

      # OAuth callback paths with bypass policy (required for OAuth to work)
      - "dockflare.0.hostname=dockflare.example.com"
      - "dockflare.0.path=/auth/google/callback"
      - "dockflare.0.service=http://dockflare:5000"
      - "dockflare.0.access.policy=bypass"

      # Add additional callback paths for other providers if needed
      - "dockflare.1.hostname=dockflare.example.com"
      - "dockflare.1.path=/auth/github/callback"
      - "dockflare.1.service=http://dockflare:5000"
      - "dockflare.1.access.policy=bypass"
```

#### **この構成が必要な理由**

- **メインインターフェースの保護:** DockFlare のダッシュボードは、選択した Access ポリシーで引き続き保護されます
- **OAuth の動作確保:** OAuth コールバックは追加の認証障壁なしで DockFlare に到達できます
- **セキュリティ:** bypass されるのは特定のコールバックパスだけで、アプリケーション全体ではありません
- **柔軟性:** IP ベースや認証ベースなど、さまざまな Access ポリシーの組み合わせで動作します

#### **重要な注意点**

1. **パスの一致:** コールバックパスは、OAuth プロバイダーが期待するものと完全に一致している必要があります
2. **複数プロバイダー:** 設定する OAuth プロバイダーごとに、個別のインデックス付きルールを追加してください
3. **ワイルドカードを使わない:** セキュリティ上の理由からワイルドカードパスは避け、具体的な callback URL を指定してください
4. **テストする:** 設定後は、保護されたメインインターフェースへのアクセスと OAuth ログインフローの両方を確認してください
