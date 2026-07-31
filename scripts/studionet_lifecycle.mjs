import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execSync } from 'node:child_process';
import { createAccount, createClient } from 'genlayer-js';
import { studionet } from 'genlayer-js/chains';

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

function sanitizeTransactions(transactions) {
  if (!transactions || typeof transactions !== 'object' || Array.isArray(transactions)) {
    return undefined;
  }
  const safe = {};
  for (const [name, transaction] of Object.entries(transactions)) {
    if (!transaction || typeof transaction !== 'object' || Array.isArray(transaction)) continue;
    const record = {};
    for (const key of ['transactionHash', 'status', 'execution', 'submittedAt', 'finalizedAt']) {
      if (transaction[key] !== undefined) record[key] = transaction[key];
    }
    safe[name] = record;
  }
  return safe;
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
    'transactions',
    'canonicalReads',
    'limits',
  ]) {
    if (key === 'transactions') {
      const transactions = sanitizeTransactions(input[key]);
      if (transactions !== undefined) output.transactions = transactions;
    } else if (input[key] !== undefined) {
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
  const projectHasPrimary = Boolean(project.GENLAYER_PRIVATE_KEY || project.STUDIONET_PRIVATE_KEY);
  const parentHasPrimary = Boolean(parent.GENLAYER_PRIVATE_KEY || parent.STUDIONET_PRIVATE_KEY);
  return {
    hasProjectPrivateKey: projectHasPrimary,
    hasParentPrivateKey: parentHasPrimary,
    hasParentIntegratorPrivateKey: Boolean(parent.STUDIONET_INTEGRATOR_PRIVATE_KEY),
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

const CONTRACT_PATH = resolve('contracts', 'filing_trigger_covenant.py');
const EVIDENCE_PATH = resolve('docs', 'evidence', 'studionet', 'deployment.json');
const RPC_URL = studionet.rpcUrls.default.http[0];
const EXPLORER_URL = 'https://explorer-studio.genlayer.com';
const COVENANT_ID = 'cyber-001';
const CIK = '732026';
const ACCESSION = '000143774926009193';
const FILING_URL = 'https://www.sec.gov/Archives/edgar/data/732026/000143774926009193/trt20260320_8k.htm';
const PAYOUT_WEI = 10_000_000_000_000_000n;
const CLAIM_BOND_WEI = 1_000_000_000_000_000n;
const TERMINAL_FAILURES = new Set([
  'UNDETERMINED',
  'CANCELED',
  'LEADER_TIMEOUT',
  'VALIDATORS_TIMEOUT',
]);

function loadEnvIntoProcess(filePath) {
  const text = readTextIfExists(filePath);
  for (const [key, value] of Object.entries(parseEnvText(text))) {
    if (process.env[key] === undefined) process.env[key] = value;
  }
}

function requirePrivateKey(names) {
  for (const name of names) {
    const value = process.env[name];
    if (value && value.trim()) return value.trim();
  }
  throw new Error(`Missing required private key variable: ${names.join(' or ')}`);
}

function jsonSafe(value) {
  if (typeof value === 'bigint') return value.toString();
  if (Array.isArray(value)) return value.map(jsonSafe);
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, jsonSafe(item)]),
    );
  }
  return value;
}

function readEvidence() {
  if (!existsSync(EVIDENCE_PATH)) return null;
  return JSON.parse(readFileSync(EVIDENCE_PATH, 'utf8'));
}

function writeEvidence(patch, { replace = false } = {}) {
  const previous = replace ? {} : (readEvidence() ?? {});
  const evidence = projectSafeEvidence({
    ...previous,
    ...patch,
    network: 'studionet',
    sourceCommit: currentCommit(),
    limits: {
      noFrontend: !existsSync(resolve('frontend')),
      contractOnlyTrack: true,
      evidenceIsSanitized: true,
    },
  });
  mkdirSync(dirname(EVIDENCE_PATH), { recursive: true });
  writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, 'utf8');
  return evidence;
}

function archiveEvidence(existing, reason) {
  if (!existing?.contractAddress) return;
  const safeAddress = String(existing.contractAddress).toLowerCase().replace(/^0x/, '');
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const archivePath = resolve(
    'docs',
    'evidence',
    'studionet',
    'archive',
    `deployment-${safeAddress}-${stamp}.json`,
  );
  mkdirSync(dirname(archivePath), { recursive: true });
  writeFileSync(
    archivePath,
    `${JSON.stringify({ ...existing, archivedReason: reason }, null, 2)}\n`,
    'utf8',
  );
}

function signingClient(account) {
  return createClient({ chain: studionet, endpoint: RPC_URL, account });
}

function publicClient() {
  return createClient({ chain: studionet, endpoint: RPC_URL });
}

async function assertStudionet(client) {
  const chainHex = await client.request({ method: 'eth_chainId', params: [] });
  const chainId = Number(BigInt(chainHex));
  if (chainId !== studionet.id) {
    throw new Error(`Connected chain ${chainId} is not studionet ${studionet.id}`);
  }
  return chainId;
}

async function waitForFinality(client, hash, retries = 240) {
  for (let attempt = 0; attempt < retries; attempt += 1) {
    const status = await client.request({
      method: 'gen_getTransactionStatus',
      params: [hash],
    });
    if (status === 'FINALIZED') return status;
    if (TERMINAL_FAILURES.has(status)) {
      throw new Error(`Transaction ${hash} reached ${status}`);
    }
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 5000));
  }
  throw new Error(`Transaction ${hash} did not finalize before timeout`);
}

function executionName(receipt) {
  const normalized =
    receipt?.txExecutionResultName ??
    receipt?.tx_execution_result_name ??
    receipt?.executionResultName;
  if (normalized) return normalized;
  const rawLeaderReceipt = receipt?.consensus_data?.leader_receipt;
  const leaderReceipt = Array.isArray(rawLeaderReceipt)
    ? rawLeaderReceipt[0]
    : rawLeaderReceipt;
  const rawExecution = leaderReceipt?.execution_result;
  if (rawExecution === 'SUCCESS') return 'FINISHED_WITH_RETURN';
  if (typeof rawExecution === 'string' && rawExecution.length > 0) {
    return 'FINISHED_WITH_ERROR';
  }
  return 'UNKNOWN';
}

function deploymentAddress(receipt) {
  return (
    receipt?.txDataDecoded?.contractAddress ??
    receipt?.tx_data_decoded?.contract_address ??
    receipt?.data?.contract_address ??
    receipt?.data?.contractAddress ??
    parseExecutionResult(receipt).contractAddress ??
    null
  );
}

async function waitForReceipt(client, hash) {
  const receipt = await client.waitForTransactionReceipt({
    hash,
    status: 'ACCEPTED',
    interval: 5000,
    retries: 120,
    fullTransaction: true,
  });
  const networkStatus = await waitForFinality(client, hash);
  return { ...receipt, networkStatus };
}

function assertExecution(receipt, operation) {
  if (receipt.networkStatus !== 'FINALIZED') {
    throw new Error(`${operation} did not finalize`);
  }
  const execution = executionName(receipt);
  if (execution !== 'FINISHED_WITH_RETURN') {
    throw new Error(`${operation} failed with ${execution}`);
  }
}

function transactionRecord(hash, receipt) {
  return {
    transactionHash: hash,
    status: receipt.networkStatus,
    execution: executionName(receipt),
    finalizedAt: new Date().toISOString(),
  };
}

async function writeFinalized(client, address, functionName, args, value = 0n, existing = null, onPending = () => {}) {
  let hash = existing?.transactionHash;
  if (!hash) {
    hash = await client.writeContract({ address, functionName, args, value });
    await onPending({ transactionHash: hash, status: 'SUBMITTED', submittedAt: new Date().toISOString() });
  }
  const receipt = await waitForReceipt(client, hash);
  assertExecution(receipt, functionName);
  return transactionRecord(hash, receipt);
}

async function readView(client, address, functionName, args = []) {
  return jsonSafe(
    await client.readContract({
      address,
      functionName,
      args,
      jsonSafeReturn: true,
    }),
  );
}

function loadAccounts() {
  loadEnvIntoProcess(resolve('.env'));
  loadEnvIntoProcess(resolve('..', '.env'));
  const sponsor = createAccount(requirePrivateKey(['GENLAYER_PRIVATE_KEY', 'STUDIONET_PRIVATE_KEY']));
  const beneficiary = createAccount(requirePrivateKey(['STUDIONET_INTEGRATOR_PRIVATE_KEY']));
  return { sponsor, beneficiary };
}

async function deploy() {
  const evidence = readEvidence();
  if (evidence?.contractAddress && evidence?.sourceCommit === currentCommit()) {
    console.log(JSON.stringify(projectSafeEvidence({ ...evidence, result: 'EXISTING_DEPLOYMENT' }), null, 2));
    return evidence.contractAddress;
  }
  let replaceEvidence = false;
  if (evidence?.contractAddress && evidence?.sourceCommit !== currentCommit()) {
    archiveEvidence(evidence, 'Source commit changed before redeploy');
    replaceEvidence = true;
  }

  const { sponsor, beneficiary } = loadAccounts();
  const client = signingClient(sponsor);
  await assertStudionet(client);
  const code = new Uint8Array(readFileSync(CONTRACT_PATH));
  const hash = await client.deployContract({ code, args: [] });
  writeEvidence({
    result: 'DEPLOY_SUBMITTED',
    transactionHash: hash,
    actorRoles: {
      sponsor: sponsor.address,
      beneficiary: beneficiary.address,
    },
  }, { replace: replaceEvidence });
  const receipt = await waitForReceipt(client, hash);
  assertExecution(receipt, 'deploy FilingTriggerCovenant');
  const address = deploymentAddress(receipt);
  if (!/^0x[0-9a-fA-F]{40}$/.test(address ?? '')) {
    throw new Error('Deployed contract address missing from receipt');
  }
  const finalEvidence = writeEvidence({
    result: 'SUCCESS',
    contractAddress: address,
    transactionHash: hash,
    timestamp: new Date().toISOString(),
    actorRoles: {
      sponsor: sponsor.address,
      beneficiary: beneficiary.address,
    },
    canonicalReads: {
      explorerAddress: `${EXPLORER_URL}/address/${address}`,
    },
  });
  console.log(JSON.stringify(finalEvidence, null, 2));
  return address;
}

async function runDemo() {
  const evidence = readEvidence();
  if (!evidence?.contractAddress) {
    throw new Error('Run deploy before run-demo');
  }
  const { sponsor, beneficiary } = loadAccounts();
  const sponsorClient = signingClient(sponsor);
  const beneficiaryClient = signingClient(beneficiary);
  await assertStudionet(sponsorClient);
  const address = evidence.contractAddress;
  const transactions = { ...(evidence.transactions ?? {}) };
  const persistPending = (name) => (pending) => {
    transactions[name] = pending;
    writeEvidence({ ...evidence, transactions });
  };

  transactions.openCovenant = await writeFinalized(
    sponsorClient,
    address,
    'open_covenant',
    [
      COVENANT_ID,
      beneficiary.address,
      CIK,
      'MATERIAL_CYBER_INCIDENT',
      '8-K',
      'Item 1.05',
      '2026-01-01',
      '2026-12-31',
      PAYOUT_WEI,
      CLAIM_BOND_WEI,
    ],
    PAYOUT_WEI,
    transactions.openCovenant,
    persistPending('openCovenant'),
  );
  transactions.acceptCovenant = await writeFinalized(
    beneficiaryClient,
    address,
    'accept_covenant',
    [COVENANT_ID],
    0n,
    transactions.acceptCovenant,
    persistPending('acceptCovenant'),
  );
  transactions.openClaim = await writeFinalized(
    beneficiaryClient,
    address,
    'open_claim',
    [COVENANT_ID, ACCESSION, FILING_URL],
    CLAIM_BOND_WEI,
    transactions.openClaim,
    persistPending('openClaim'),
  );
  transactions.adjudicateClaim = await writeFinalized(
    sponsorClient,
    address,
    'adjudicate_claim',
    [COVENANT_ID],
    0n,
    transactions.adjudicateClaim,
    persistPending('adjudicateClaim'),
  );

  const beforeWithdrawCredit = await readView(beneficiaryClient, address, 'get_credit', [beneficiary.address]);
  if (BigInt(beforeWithdrawCredit) > 0n) {
    transactions.withdrawCredit = await writeFinalized(
      beneficiaryClient,
      address,
      'withdraw_credit',
      [BigInt(beforeWithdrawCredit)],
      0n,
      transactions.withdrawCredit,
      persistPending('withdrawCredit'),
    );
  }
  const canonicalReads = {
    status: await readView(sponsorClient, address, 'get_status', [COVENANT_ID]),
    covenant: await readView(sponsorClient, address, 'get_covenant', [COVENANT_ID]),
    claim: await readView(sponsorClient, address, 'get_claim', [COVENANT_ID]),
    beneficiaryCreditBeforeWithdraw: beforeWithdrawCredit,
    beneficiaryCreditAfterWithdraw: await readView(beneficiaryClient, address, 'get_credit', [beneficiary.address]),
    accounting: await readView(sponsorClient, address, 'get_accounting', []),
  };
  const finalEvidence = writeEvidence({
    ...evidence,
    result: 'SUCCESS',
    contractAddress: address,
    transactionHash: evidence.transactionHash,
    actorRoles: {
      sponsor: sponsor.address,
      beneficiary: beneficiary.address,
    },
    covenantId: COVENANT_ID,
    claimAccession: ACCESSION,
    transactions,
    canonicalReads,
  });
  console.log(JSON.stringify(projectSafeEvidence(finalEvidence), null, 2));
}

async function inspect() {
  const projectEnv = readTextIfExists(resolve('.env'));
  const parentEnv = readTextIfExists(resolve('..', '.env'));
  const currentEvidence = readEvidence();
  const evidence = projectSafeEvidence({
    network: 'studionet',
    sourceCommit: currentCommit(),
    result: currentEvidence?.result ?? 'PENDING_DEPLOYMENT',
    contractAddress: currentEvidence?.contractAddress,
    transactionHash: currentEvidence?.transactionHash,
    canonicalReads: currentEvidence?.canonicalReads,
    limits: discoverEnvPresence({ projectEnv, parentEnv }),
  });
  console.log(JSON.stringify(evidence, null, 2));
}

async function main() {
  const command = process.argv[2] || 'inspect';
  if (command === 'inspect') {
    await inspect();
    return;
  }
  if (command === 'deploy') {
    await deploy();
    return;
  }
  if (command === 'run-demo') {
    await runDemo();
    return;
  }
  console.error(`Unknown command: ${command}`);
  process.exitCode = 2;
}

const isCli = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isCli) {
  main().catch((error) => {
    console.error(String(error?.message ?? error));
    process.exitCode = 1;
  });
}
