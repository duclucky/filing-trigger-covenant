import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execSync } from 'node:child_process';

export function parseExecutionResult(receipt) {
  const raw = receipt?.consensus_data?.leader_receipt?.[0]?.execution_result;
  if (raw) {
    return {
      result: raw.result ?? raw.status ?? 'UNKNOWN',
      contractAddress: raw.contract_address ?? raw.contractAddress ?? null,
      returnData: raw.return_data ?? raw.returnData ?? null,
      ...(raw.error ? { error: String(raw.error) } : {}),
    };
  }

  const normalized = receipt?.executionResult ?? receipt?.execution_result;
  if (normalized) {
    return {
      result: normalized.result ?? normalized.status ?? 'UNKNOWN',
      contractAddress: normalized.contractAddress ?? normalized.contract_address ?? null,
      returnData: normalized.returnData ?? normalized.return_data ?? null,
      ...(normalized.error ? { error: String(normalized.error) } : {}),
    };
  }

  return {
    result: 'UNKNOWN',
    contractAddress: null,
    returnData: null,
  };
}

export function projectSafeEvidence(input) {
  const output = {};
  for (const key of [
    'network',
    'sourceCommit',
    'contractAddress',
    'transactionHash',
    'result',
    'timestamp',
    'actorRoles',
    'covenantId',
    'claimAccession',
    'canonicalReads',
    'limits',
  ]) {
    if (input[key] !== undefined) {
      output[key] = input[key];
    }
  }
  return output;
}

function parseEnvText(text) {
  const result = {};
  for (const rawLine of String(text || '').split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const index = line.indexOf('=');
    if (index <= 0) continue;
    result[line.slice(0, index).trim()] = line.slice(index + 1).trim();
  }
  return result;
}

export function discoverEnvPresence({ projectEnv = '', parentEnv = '' } = {}) {
  const project = parseEnvText(projectEnv);
  const parent = parseEnvText(parentEnv);
  return {
    hasProjectPrivateKey: Boolean(project.GENLAYER_PRIVATE_KEY),
    hasParentPrivateKey: Boolean(parent.GENLAYER_PRIVATE_KEY),
    hasSecUserAgent: Boolean(project.SEC_USER_AGENT || parent.SEC_USER_AGENT),
  };
}

function readTextIfExists(path) {
  return existsSync(path) ? readFileSync(path, 'utf8') : '';
}

function currentCommit() {
  try {
    return execSync('git rev-parse HEAD', { encoding: 'utf8' }).trim();
  } catch {
    return 'UNKNOWN';
  }
}

function inspect() {
  const projectEnv = readTextIfExists(resolve('.env'));
  const parentEnv = readTextIfExists(resolve('..', '.env'));
  const evidence = projectSafeEvidence({
    network: 'studionet',
    sourceCommit: currentCommit(),
    result: 'PENDING_DEPLOYMENT',
    limits: discoverEnvPresence({ projectEnv, parentEnv }),
  });
  console.log(JSON.stringify(evidence, null, 2));
}

function notImplemented(command) {
  console.error(`${command} requires Task 6 studionet transaction implementation.`);
  process.exitCode = 2;
}

function main() {
  const command = process.argv[2] || 'inspect';
  if (command === 'inspect') {
    inspect();
    return;
  }
  if (command === 'deploy' || command === 'run-demo') {
    notImplemented(command);
    return;
  }
  console.error(`Unknown command: ${command}`);
  process.exitCode = 2;
}

const isCli = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isCli) {
  main();
}

