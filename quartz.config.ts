import { QuartzConfig } from "./quartz/cfg"
import * as Plugin from "./quartz/plugins"

const config: QuartzConfig = {
  configuration: {
    pageTitle: "学习笔记",
    pageTitleSuffix: "",
    enableSPA: true,
    enablePopovers: true,
    analytics: null,
    locale: "zh-CN",
    baseUrl: "laoyutong.github.io/blog-content",
    ignorePatterns: [
      "private",
      "templates",
      ".obsidian",
      "site",
      "docs",
      "content",
      "quartz",
      "node_modules",
      ".github",
      "*.json",
      "*.ts",
      "*.js",
      "*.py",
      "*.yml",
      "README.md",
    ],
    defaultDateType: "modified",
    theme: {
      fontOrigin: "googleFonts",
      cdnCaching: true,
      typography: {
        title: "Noto Serif SC",
        header: "Noto Sans SC",
        body: "Noto Serif SC",
        code: "JetBrains Mono",
      },
      colors: {
        lightMode: {
          light: "#f6f7f9",
          lightgray: "#dfe3e8",
          gray: "#8f99a6",
          darkgray: "#374151",
          dark: "#111827",
          secondary: "#2563eb",
          tertiary: "#64748b",
          highlight: "rgba(37, 99, 235, 0.08)",
          textHighlight: "#fff3a366",
        },
        darkMode: {
          light: "#f6f7f9",
          lightgray: "#dfe3e8",
          gray: "#8f99a6",
          darkgray: "#374151",
          dark: "#111827",
          secondary: "#2563eb",
          tertiary: "#64748b",
          highlight: "rgba(37, 99, 235, 0.08)",
          textHighlight: "#fff3a366",
        },
      },
    },
  },
  plugins: {
    transformers: [
      Plugin.FrontMatter(),
      Plugin.CreatedModifiedDate({
        priority: ["frontmatter", "git", "filesystem"],
      }),
      Plugin.SyntaxHighlighting({
        theme: {
          light: "github-light",
          dark: "github-dark",
        },
        keepBackground: false,
      }),
      Plugin.ObsidianFlavoredMarkdown({ enableInHtmlEmbed: false }),
      Plugin.GitHubFlavoredMarkdown(),
      Plugin.HardLineBreaks(),
      Plugin.TableOfContents(),
      Plugin.CrawlLinks({ markdownLinkResolution: "shortest" }),
      Plugin.Description(),
      Plugin.Latex({ renderEngine: "katex" }),
    ],
    filters: [Plugin.RemoveDrafts()],
    emitters: [
      Plugin.AliasRedirects(),
      Plugin.ComponentResources(),
      Plugin.ContentPage(),
      Plugin.FolderPage(),
      Plugin.TagPage(),
      Plugin.ContentIndex({
        enableSiteMap: true,
        enableRSS: true,
      }),
      Plugin.Assets(),
      Plugin.Static(),
      Plugin.Favicon(),
      Plugin.NotFoundPage(),
      // Comment out CustomOgImages to speed up build time
      Plugin.CustomOgImages(),
    ],
  },
}

export default config
