import fs from 'node:fs'
import { execFileSync } from 'node:child_process'

const baseRef = process.env.RELEASE_BASE_REF || process.argv[2] || 'origin/staging'
const packagePath = 'web/package.json'
const changelogPath = 'CHANGELOG.md'

function fail(message) {
  console.error(`release gate failed: ${message}`)
  process.exit(1)
}

function git(args) {
  return execFileSync('git', args, { encoding: 'utf8' }).trim()
}

function versionOf(packageJson) {
  const version = JSON.parse(packageJson).version
  if (!/^\d+\.\d+\.\d+$/.test(version)) fail(`web/package.json version must be x.y.z, got ${version}`)
  return version
}

function newerThan(current, previous) {
  const a = current.split('.').map(Number)
  const b = previous.split('.').map(Number)
  for (let i = 0; i < 3; i += 1) {
    if (a[i] > b[i]) return true
    if (a[i] < b[i]) return false
  }
  return false
}

function releaseNotes(changelog, version) {
  const header = new RegExp(`^##\\s+\\[?${version}\\]?.*$`, 'm')
  const match = changelog.match(header)
  if (!match || match.index === undefined) return ''
  const rest = changelog.slice(match.index + match[0].length)
  const next = rest.search(/^##\s+\[?\d+\.\d+\.\d+/m)
  return (next === -1 ? rest : rest.slice(0, next)).trim()
}

const currentVersion = versionOf(fs.readFileSync(packagePath, 'utf8'))
let previousVersion = '0.0.0'
try {
  previousVersion = versionOf(git(['show', `${baseRef}:${packagePath}`]))
} catch {
  console.warn(`release gate warning: could not read ${packagePath} from ${baseRef}; using ${previousVersion}`)
}

if (!newerThan(currentVersion, previousVersion)) {
  fail(`web/package.json version ${currentVersion} must be greater than ${previousVersion}`)
}

const changedFiles = git(['diff', '--name-only', `${baseRef}...HEAD`]).split('\n').filter(Boolean)
if (!changedFiles.includes(changelogPath)) fail(`${changelogPath} must be changed`)

const notes = releaseNotes(fs.readFileSync(changelogPath, 'utf8'), currentVersion)
if (!notes || /No release notes found/i.test(notes)) {
  fail(`${changelogPath} needs release notes for ${currentVersion}`)
}

console.log(`release gate passed: ${previousVersion} -> ${currentVersion}`)
