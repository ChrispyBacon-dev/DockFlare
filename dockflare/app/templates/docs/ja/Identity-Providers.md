# アイデンティティプロバイダー

> **📌 重要:** このガイドは、サービスやアプリケーションを保護するために **Cloudflare Access ポリシー用のアイデンティティプロバイダー** を構成するためのものです。**DockFlare 管理画面へのログイン**用に OAuth/OIDC を設定したい場合は、代わりに [OAuth プロバイダーのセットアップ](OAuth-Provider-Setup.md) を参照してください。

アイデンティティプロバイダー（IdP）を使うと、Cloudflare Zero Trust で保護されたアプリケーションに OAuth/OIDC 認証を導入できます。DockFlare では、IdP の管理や Access ポリシーへの統合を簡単に行えます。

## 概要

メールベースの認証だけに依存する代わりに、Google、GitHub、Azure AD などの一般的な OAuth プロバイダーを利用できます。ユーザーは既存のアカウントで認証できるため、スムーズで安全なログイン体験を提供できます。

## サポートされているプロバイダー

DockFlare は次のアイデンティティプロバイダーをサポートしています。

- **Google** - 個人向け Google アカウント
- **Google Workspace** - オプションのドメイン制限付き Google Workspace（G Suite）アカウント
- **Microsoft Azure AD** - Microsoft Entra ID（Azure Active Directory）
- **Okta** - Okta Identity Cloud
- **GitHub** - GitHub OAuth
- **汎用 OpenID Connect** - OIDC 準拠の任意のプロバイダー

## アイデンティティプロバイダーの管理

### アイデンティティプロバイダーを追加する

1. **Access Policies** ページを開きます。
2. **Identity Providers** セクションで **Add Provider** をクリックします。
3. 必須項目を入力します。
   - **Friendly Name**: DockFlare 内部で使う名前。例: `google-main`、`github-dev`
   - **Display Name**: Cloudflare ダッシュボードに表示される名前
   - **Provider Type**: 使用する OAuth プロバイダー
   - **Configuration**: プロバイダー固有の認証情報。下のセットアップガイドを参照してください
4. **Create Provider** をクリックします。
5. 提供されるテスト URL でプロバイダーを確認します。

### Cloudflare から同期する

Cloudflare Zero Trust ですでに IdP を設定している場合:

1. Identity Providers セクションで **Sync from Cloudflare** をクリックします。
2. DockFlare は既存の IdP をすべて取り込み、自動的に Friendly Name を生成します。
3. ラベルから参照しやすいように、あとで Friendly Name を変更することもできます。

### アイデンティティプロバイダーをテストする

IdP を作成したあとで、すぐにテストできます。

1. 対象のプロバイダーの横にある **⋮** メニューをクリックします。
2. **Test IdP** を選択します。
3. 新しいウィンドウが開き、認証を試せます。
4. ログインフローが正しく動作することを確認します。

## プロバイダーのセットアップガイド

### Google（個人アカウント）

**ステップ 1: OAuth 認証情報を作成する**

1. [Google Cloud Console](https://console.cloud.google.com/) を開きます。
2. 新しいプロジェクトを作成するか、既存のプロジェクトを選択します。
3. **API とサービス** → **認証情報** に移動します。
4. **Create Credentials** → **OAuth client ID** をクリックします。
5. **Web application** を選択します。
6. 承認済みリダイレクト URI を追加します。
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>チーム名は <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> の Settings > Custom Pages で確認できます。</small>
7. **Client ID** と **Client Secret** をコピーします。

**ステップ 2: DockFlare で設定する**

- **Client ID**: Google Cloud Console の値を貼り付けます
- **Client Secret**: Google Cloud Console の値を貼り付けます

---

### Google Workspace

基本的には上記の Google 設定と同じですが、追加のオプション項目があります。

- **Apps Domain**: （任意）`example.com` のような特定ドメインに制限します

この項目を指定すると、`@example.com` のメールアドレスを持つユーザーだけが認証できます。

---

### Microsoft Azure AD

**ステップ 1: Azure にアプリケーションを登録する**

1. [Azure ポータル](https://portal.azure.com/) を開きます。
2. **Azure Active Directory** → **App registrations** に移動します。
3. **New registration** をクリックします。
4. アプリケーション名を設定します。例: `DockFlare Access`
5. **Redirect URI** で **Web** を選択し、次を入力します。
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>チーム名は <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> の Settings > Custom Pages で確認できます。</small>
6. **Register** をクリックします。
7. **Application (client) ID** をコピーします。
8. **Directory (tenant) ID** をコピーします。
9. **Certificates & secrets** → **New client secret** に進みます。
10. シークレットを作成し、**Value** をコピーします。

**ステップ 2: DockFlare で設定する**

- **Application (client) ID**: Azure の値を貼り付けます
- **Directory (tenant) ID**: Azure の値を貼り付けます
- **Client Secret**: Azure の値を貼り付けます

---

### GitHub

**ステップ 1: OAuth アプリを作成する**

1. [GitHub Developer Settings](https://github.com/settings/developers) を開きます。
2. **New OAuth App** をクリックします。
3. 次の内容を入力します。
   - **Application name**: DockFlare Access
   - **Homepage URL**: `https://your-domain.com`
   - **Authorization callback URL**:
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>チーム名は <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> の Settings > Custom Pages で確認できます。</small>
4. **Register application** をクリックします。
5. **Client ID** をコピーします。
6. **Generate a new client secret** をクリックしてシークレットをコピーします。

**ステップ 2: DockFlare で設定する**

- **Client ID**: GitHub の値を貼り付けます
- **Client Secret**: GitHub の値を貼り付けます

---

### Okta

**ステップ 1: Okta でアプリケーションを作成する**

1. [Okta Admin Console](https://admin.okta.com/) にログインします。
2. **Applications** → **Create App Integration** に移動します。
3. **OIDC - OpenID Connect** を選択します。
4. **Web Application** を選択します。
5. 次を設定します。
   - **Sign-in redirect URIs**:
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>チーム名は <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> の Settings > Custom Pages で確認できます。</small>
6. **Save** をクリックします。
7. **Client ID** と **Client Secret** をコピーします。
8. **Okta domain**（例: `https://dev-12345.okta.com`）を控えておきます。

**ステップ 2: DockFlare で設定する**

- **Okta Account URL**: Okta ドメイン。例: `https://dev-12345.okta.com`
- **Client ID**: Okta の値を貼り付けます
- **Client Secret**: Okta の値を貼り付けます

---

### 汎用 OpenID Connect

OIDC 準拠の任意のプロバイダーについて:

**ステップ 1: プロバイダー設定を取得する**

IdP のドキュメントから次の情報を取得します。
- Authorization URL
- Token URL
- JWKS URL（JSON Web Key Set）
- Client ID
- Client Secret

**ステップ 2: DockFlare で設定する**

- **Authorization URL**: プロバイダーの OAuth 認可エンドポイント
- **Token URL**: プロバイダーのトークンエンドポイント
- **JWKS URL**: 署名検証に使うプロバイダーの JWKS エンドポイント
- **Client ID**: プロバイダーから取得した値
- **Client Secret**: プロバイダーから取得した値

---

## Access ポリシーでアイデンティティプロバイダーを使う

### Access Groups で使う

1. **Access Policies** → **Advanced Access Policies** に移動します。
2. **Create New Group** をクリックするか、既存グループを編集します。
3. **Policy Rules** セクションで:
   - **Identity Providers**: 1 つ以上の IdP を選択します
   - **Allowed Emails or Domains**: **IdP を使う場合は必須**です。許可するメールアドレスを指定します
4. グループを保存します。

### 認証モード

次の 2 つの方法があります。

1. **Email Only**: メールアドレスを入力し、IdP は選択しません。ユーザーはワンタイム PIN で認証します。
2. **IdP + Email (Required)**: IdP を選択し、許可するメールアドレスを入力します。ユーザーは選択した IdP 経由で認証し、かつ許可リストに含まれている必要があります。

**⚠️ セキュリティ上の注意:** アイデンティティプロバイダーを使う場合は、許可するメールアドレスを**必ず**指定してください。たとえばメール制限を設定しないまま `Google` を IdP として使うと、任意の Google アカウントを持つ人がサービスにアクセスできてしまいます。

### Docker ラベルで使う

コンテナラベルでは Friendly Name を使います。

```yaml
services:
  myapp:
    image: myapp:latest
    labels:
      dockflare.enable: "true"
      dockflare.hostname: "app.example.com"
      dockflare.access.group: "my-access-group"
```

アクセスグループ `my-access-group` は、IdP の Friendly Name を自動的に Cloudflare UUID に変換します。

---

## ベストプラクティス

### 命名規則

わかりやすく説明的な名前を使ってください。
- ✅ `google-main`、`github-dev`、`azure-work`
- ❌ `idp1`、`test`、`new`

### セキュリティ

- **シークレットを定期的にローテーションする**: Client Secret を定期的に更新します
- **範囲を制限する**: Google Workspace と Azure AD は、可能であれば特定ドメインに制限します
- **本番投入前にテストする**: 本番サービスに適用する前に必ず IdP をテストしてください
- **利用状況を監視する**: Cloudflare のログを確認し、不正アクセスの試行を検出します

### 複数環境

環境ごとに別々の IdP を作成します。
- `google-dev` - 開発環境
- `google-staging` - ステージング環境
- `google-prod` - 本番環境

### IdP 利用時のメール要件

**重要:** IdP 認証では、安全のため常にメールアドレスの制限が必要です。

**Access Group の例:**
- **Identity Providers**: `google-main`
- **Allowed Emails**: `admin@example.com, user@example.com, @contractor-domain.com`

この設定では、次のユーザーにアクセスを許可します。
- `google-main` IdP（Google OAuth）を通じて認証し、**かつ**
- `admin@example.com`、`user@example.com`、または任意の `@contractor-domain.com` に一致するメールアドレスを持っていること

**仕組み:**
1. ユーザーが保護されたアプリケーションでサインインをクリックします。
2. Google OAuth ログインへリダイレクトされます。
3. Google 認証後、Cloudflare がそのメールアドレスが許可リストにあるか確認します。
4. メールアドレスが許可リストに一致する場合のみアクセスが許可されます。

---

## トラブルシューティング

### 「Invalid Redirect URI」エラー

**原因:** OAuth プロバイダー側の Redirect URI が、Cloudflare が期待する URI と一致していません。

**解決策:** 次の Redirect URI が正確に追加されていることを確認してください。
```
https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
```
<small>チーム名は <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> の Settings > Custom Pages で確認できます。</small>

`<your-team>` を Cloudflare Zero Trust のチーム名に置き換えてください。

---

### 「IdP Test Failed」

**原因:** 認証情報または設定が正しくありません。

**解決策:**
1. Client ID と Client Secret が正しいことを確認します
2. OAuth アプリケーションがプロバイダー側で有効になっていることを確認します
3. Azure AD の場合は Client ID と Tenant ID の両方を確認します
4. Cloudflare のテスト URL を使ってプロバイダーを確認します

---

### 「Cannot Delete System-Managed IdP」

**原因:** 組み込みの One-Time PIN プロバイダーを削除しようとしています。

**解決策:** `onetimepin` プロバイダーはシステム管理されているため削除できません。メールベースの OTP 認証に必要です。

---

### 「IdP Not Found in Docker Label」

**原因:** ラベル内で Friendly Name ではなく Cloudflare UUID を使っています。

**解決策:** アクセスグループ設定では UUID の代わりに `google-main` のような Friendly Name を使ってください。

---

## 関連ドキュメント

- [アクセス ポリシーのベストプラクティス](Access-Policy-Best-Practices.md)
- [ゾーンのデフォルトポリシー](Zone-Default-Policies.md)
- [コンテナラベル](Container-Labels.md)
- [セキュリティアーキテクチャ](Security-Architecture.md)

---
