import fs from 'node:fs';
import path from 'node:path';

export default function(eleventyConfig) {
  // Existing pages remain exact copies until each is deliberately migrated.
  for (const entry of fs.readdirSync('src', {withFileTypes:true})) {
    if (entry.isFile() && !entry.name.endsWith('.md') && !entry.name.endsWith('.njk')) {
      eleventyConfig.addPassthroughCopy(path.join('src', entry.name));
    }
  }
  eleventyConfig.addPassthroughCopy('src/images');
  for (const entry of fs.readdirSync('src/articles')) {
    if (entry.endsWith('.html')) eleventyConfig.addPassthroughCopy(path.join('src/articles', entry));
  }
  eleventyConfig.addFilter('dateISO', value => new Date(value).toISOString().slice(0,10));
  eleventyConfig.addFilter('displayDate', value =>
    'Published on ' + new Intl.DateTimeFormat('en-CA', {timeZone:'UTC',year:'numeric',month:'long',day:'numeric'}).format(new Date(value)));
  eleventyConfig.addFilter('trimLeadingSlash', value => value.replace(/^\//,''));
  return {
    dir: { input: 'src', includes: '_includes', output: '_site' },
    templateFormats: ['md','njk'],
    markdownTemplateEngine: 'njk',
    htmlTemplateEngine: false,
    passthroughFileCopy: true
  };
}
