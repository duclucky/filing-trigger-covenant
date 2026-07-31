import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  discoverEnvPresence,
  parseExecutionResult,
  projectSafeEvidence,
} from '../scripts/studionet_lifecycle.mjs';

test('parses raw Studio leader receipt execution result', () => {
  const raw = {
    hash: '0xabc',
    status: 'FINALIZED',
    consensus_data: {
      leader_receipt: [
        {
          execution_result: {
            result: 'SUCCESS',
            contract_address: '0x123',
            return_data: { ok: true },
          },
        },
      ],
    },
  };

  assert.deepEqual(parseExecutionResult(raw), {
    result: 'SUCCESS',
    contractAddress: '0x123',
    returnData: { ok: true },
  });
});

test('parses normalized SDK execution result', () => {
  const normalized = {
    executionResult: {
      result: 'ERROR',
      contractAddress: null,
      returnData: null,
      error: 'schema failed',
    },
  };

  assert.deepEqual(parseExecutionResult(normalized), {
    result: 'ERROR',
    contractAddress: null,
    returnData: null,
    error: 'schema failed',
  });
});

test('projects safe evidence and drops private node config', () => {
  const projected = projectSafeEvidence({
    network: 'studionet',
    contractAddress: '0x123',
    transactionHash: '0xabc',
    result: 'SUCCESS',
    actorRoles: { sponsor: '0xaaa', beneficiary: '0xbbb' },
    node_config: { private_key: 'must-not-appear' },
    stderr: 'must-not-appear',
  });

  assert.deepEqual(projected, {
    network: 'studionet',
    contractAddress: '0x123',
    transactionHash: '0xabc',
    result: 'SUCCESS',
    actorRoles: { sponsor: '0xaaa', beneficiary: '0xbbb' },
  });
  assert.equal(JSON.stringify(projected).includes('must-not-appear'), false);
});

test('env discovery reports presence without values', () => {
  const presence = discoverEnvPresence({
    projectEnv: 'GENLAYER_PRIVATE_KEY=secret\nSEC_USER_AGENT=agent\n',
    parentEnv: 'GENLAYER_PRIVATE_KEY=parent-secret\n',
  });

  assert.deepEqual(presence, {
    hasProjectPrivateKey: true,
    hasParentPrivateKey: true,
    hasSecUserAgent: true,
  });
});
