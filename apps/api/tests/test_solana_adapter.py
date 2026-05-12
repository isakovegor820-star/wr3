import pytest

from wr3_api.domain.enums import Chain
from wr3_api.domain.schemas import CreateAuditRequest
from wr3_api.services.audit_service import AuditService


@pytest.mark.asyncio
async def test_solana_heuristic_adapter_flags_unchecked_accounts():
    service = AuditService()
    record = await service.create_audit(
        CreateAuditRequest(
            chain=Chain.SOLANA,
            address="11111111111111111111111111111111",
            source="""
            use anchor_lang::prelude::*;
            #[derive(Accounts)]
            pub struct Withdraw<'info> {
              pub vault: UncheckedAccount<'info>,
            }
            pub fn withdraw(ctx: Context<Withdraw>) -> Result<()> { Ok(()) }
            """,
        )
    )
    await service.process_audit(record.audit_id)
    record = service.get_record(record.audit_id)

    assert record.state == "completed"
    assert any(finding.taxonomy.wr3_category == "solana_account_validation" for finding in record.findings)
    assert any(run.engine == "wr3_heuristic_solana" for run in record.engine_runs)


@pytest.mark.asyncio
async def test_solana_heuristic_adapter_flags_signer_and_pda_footguns():
    service = AuditService()
    record = await service.create_audit(
        CreateAuditRequest(
            chain=Chain.SOLANA,
            address="11111111111111111111111111111112",
            source="""
            use anchor_lang::prelude::*;
            #[derive(Accounts)]
            pub struct Update<'info> {
              pub authority: AccountInfo<'info>,
              #[account(mut)]
              pub vault: AccountInfo<'info>,
            }
            pub fn update(ctx: Context<Update>) -> Result<()> { Ok(()) }
            """,
        )
    )
    await service.process_audit(record.audit_id)
    record = service.get_record(record.audit_id)
    categories = {finding.taxonomy.wr3_category for finding in record.findings}

    assert "solana_signer" in categories
    assert "solana_pda" in categories
