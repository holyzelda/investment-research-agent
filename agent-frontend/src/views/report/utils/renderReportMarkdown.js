import MarkdownIt from 'markdown-it'

const markdown = new MarkdownIt({ html: false, linkify: false, typographer: false, breaks: false })
markdown.disable(['table', 'fence', 'code', 'image'])
markdown.renderer.rules.link_open = () => ''
markdown.renderer.rules.link_close = () => ''

export function renderReportMarkdown(value) {
  return markdown.render(String(value || ''))
}
