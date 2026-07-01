import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const rootDir = path.resolve(__dirname, '..')
const webDir = path.join(rootDir, 'web')

// 1. Get the current version from web/package.json
const packageJsonPath = path.join(webDir, 'package.json')
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'))
const currentVersion = packageJson.version

console.log(`Generating version.json for v${currentVersion}...`)

// 2. Read the CHANGELOG.md
const changelogPath = path.join(rootDir, 'CHANGELOG.md')
const changelogContent = fs.readFileSync(changelogPath, 'utf8')

// 3. Extract the release notes for the current version
// Matches exactly "## [x.y.z]" or "## x.y.z" optionally followed by dates or text
const versionRegex = new RegExp(`^##\\s+\\[?${currentVersion}\\]?.*$`, 'm')
const match = changelogContent.match(versionRegex)

let releaseNotes = ''

if (match && match.index !== undefined) {
  const startIndex = match.index
  
  // Find the start of the NEXT version header, if it exists
  const nextVersionRegex = /^##\s+\[?\d+\.\d+\.\d+/gm
  
  // Move past the current match
  nextVersionRegex.lastIndex = startIndex + match[0].length
  
  const nextMatch = nextVersionRegex.exec(changelogContent)
  
  if (nextMatch) {
    releaseNotes = changelogContent.substring(startIndex, nextMatch.index).trim()
  } else {
    // If no next version, take the rest of the file
    releaseNotes = changelogContent.substring(startIndex).trim()
  }
} else {
  console.warn(`⚠️ Warning: Could not find release notes for version ${currentVersion} in CHANGELOG.md`)
  releaseNotes = `## UnmessIt.AI ${currentVersion}\n\n*No release notes found in CHANGELOG.md.*`
}

// 4. Write to web/public/version.json
const outputData = {
  version: currentVersion,
  changelog: releaseNotes
}

const outputPath = path.join(webDir, 'public', 'version.json')
fs.writeFileSync(outputPath, JSON.stringify(outputData, null, 2))

console.log(`✅ Successfully generated ${outputPath}`)
