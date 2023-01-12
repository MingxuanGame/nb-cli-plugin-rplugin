<!-- markdownlint-disable MD033 MD041 -->
<p align="center">
  <img src="https://cli.nonebot.dev/logo.png" width="200" height="200" alt="nonebot">
</p>

<div align="center">

# NB CLI Plugin RPlugin

_✨ NoneBot2 命令行工具 富文本插件管理 ✨_

</div>

## 安装

使用 nb-cli

```shell
nb self install nb-cli-plugin-rplugin
```

使用 pipx

```shell
pipx inject nb-cli nb-cli-plugin-rplugin
```

## 使用

- `nb rplugin` 交互式使用 RPlugin
  - `nb rplugin list` 查看插件商店
  - `nb rplugin search` 搜索插件商店
  - `nb rplugin info` 查看插件详细信息

## 开发

参考 [CLI 插件开发文档](https://cli.nonebot.dev/docs/guide/plugin/)

### 翻译

生成模板

```shell
pdm lgenerate
```

初始化语言翻译文件或者更新现有语言翻译文件

```shell
pdm linit
```

更新语言翻译文件

```shell
pdm lupdate
```

编译语言翻译文件

```shell
pdm lcompile
```
