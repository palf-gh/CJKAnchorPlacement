# CJKAnchorPlacement

A Glyphs tool plugin that allows you to edit LSB/RSB/TSB/BSB anchors rather intuitively.

Upstream: [morisawa-inc/CJKAnchorPlacement](https://github.com/morisawa-inc/CJKAnchorPlacement). This fork adds a **Body / BBox** switch on the tool and a **Glyphs 3** reporter bundle (`CJKAnchorPlacementBatch.glyphsReporter`): same rules in the inspector while the reporter is shown, including **bulk** apply when several glyphs are selected in Edit View. Install either or both bundles.

![](CJKAnchorPlacement.png)

## Installation

1. Download the ZIP archive and unpack it, or clone the repository.
2. Double-click `CJKAnchorPlacement.glyphsTool` and/or `CJKAnchorPlacementBatch.glyphsReporter` in the Finder. Confirm in Glyphs.
3. Restart Glyphs.

## Usage (toolbar tool)

1. Select the tool in the toolbar.
2. Choose `Body` or `BBox` in the inspector.
3. Edit the LSB/RSB/TSB/BSB fields; use arrow keys to step values.

`Body` — anchors from the virtual body edges (original behaviour). `BBox` — anchors from the layer bounding box (outward positive offsets).

###### Toolbar Icon

![](CJKAnchorPlacementIcon.png)

###### Inspector View

![](CJKAnchorPlacementView.png)

## Batch reporter (Glyphs 3)

Unlike the toolbar tool, **View → CJK Anchor Placement Batch** keeps the inspector UI available whenever you are in **Edit View** — not only with a multi-glyph selection. One glyph is fine; with several selected, edits apply to all. Same **Body / BBox** rules as the tool.

## Tips

By default, the shortcut for this tool is set to the `N` key. If you want to customise it, run the following command in the Terminal:

```
$ defaults write com.GeorgSeifert.Glyphs2 CJKAnchorPlacementTool.Hotkey 'j'
```

Make sure to enter the key name you want in lowercase. To reset the shortcut to default, run the following:

```
$ defaults delete com.GeorgSeifert.Glyphs2 CJKAnchorPlacementTool.Hotkey
```

## Requirements

This fork is **only verified here on Glyphs 3.4.1**. The batch reporter needs **Glyphs 3**; other versions may work but we have not tested them.

## Modification Notice

This fork extends the Apache-2.0-licensed upstream tool with a `Body` / `BBox` reference-mode switch (`BBox` uses outward distances from the layer bounding box) and adds the **CJKAnchorPlacementBatch** reporter bundle (Glyphs 3) for bulk editing in Edit View under the same rules.

## License

Apache License 2.0

---

## 日本語

Glyphs 用のツールプラグインで、LSB / RSB / TSB / BSB アンカーを直感的に編集できます。

フォーク元: [morisawa-inc/CJKAnchorPlacement](https://github.com/morisawa-inc/CJKAnchorPlacement)。本フォークではツールに **Body / BBox** の切り替えを追加し、**Glyphs 3** 用レポーターバンドル（`CJKAnchorPlacementBatch.glyphsReporter`）を同梱しています。レポーターを表示しているあいだはインスペクタでツールと同じルールが使え、編集ビューで複数グリフを選んでいるときは一括で反映されます。どちらか一方のバンドルだけでも、両方でもインストールできます。

![](CJKAnchorPlacement.png)

### インストール

1. ZIP を展開するか、リポジトリをクローンします。
2. Finder で `CJKAnchorPlacement.glyphsTool` と／または `CJKAnchorPlacementBatch.glyphsReporter` をダブルクリックし、Glyphs で確認します。
3. Glyphs を再起動します。

### 使い方（ツールバー）

1. ツールバーでツールを選びます。
2. インスペクタで `Body` か `BBox` を選びます。
3. LSB / RSB / TSB / BSB のフィールドを編集します。矢印キーで値を増減できます。

**Body** — 仮想ボディの辺から（従来どおり）。**BBox** — レイヤーのバウンディングボックスを基準に、正の値はボックスの外側へオフセットします。

###### ツールバーアイコン

![](CJKAnchorPlacementIcon.png)

###### インスペクタ

![](CJKAnchorPlacementView.png)

### バッチレポーター（Glyphs 3）

ツールバー用ツールとは異なり、**表示 → CJK Anchor Placement Batch** をオンにすると、**編集ビュー**にいる限りインスペクタの UI が常に使えます。複数グリフに限りません。1 グリフでも構いません。複数選んだときは編集はすべての選択に適用されます。**Body / BBox** のルールはツールと同じです。

### Tips

既定のショートカットは `N` キーです。変更するにはターミナルで次を実行します。

```
$ defaults write com.GeorgSeifert.Glyphs2 CJKAnchorPlacementTool.Hotkey 'j'
```

キー名は小文字で指定してください。既定に戻すには次を実行します。

```
$ defaults delete com.GeorgSeifert.Glyphs2 CJKAnchorPlacementTool.Hotkey
```

### 動作要件

このフォークは **Glyphs 3.4.1** でのみこちらで動作確認しています。バッチレポーターは **Glyphs 3** が必要です。その他のバージョンでも動く可能性はありますが、未検証です。

### 改変について

Apache License 2.0 の上流ツールに対し、本フォークでは `Body` / `BBox` の参照モード切り替え（**BBox** はレイヤーのバウンディングボックスの外側への距離）を追加し、あわせて **Glyphs 3** 向けバッチレポーター `CJKAnchorPlacementBatch.glyphsReporter` を追加しています。

### ライセンス

Apache License 2.0
