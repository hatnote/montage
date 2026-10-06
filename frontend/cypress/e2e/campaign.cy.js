// #510: a clean check of one file, valid from now on
const stubCheck = () => {
  const now = Date.now()
  cy.intercept('POST', '/v1/admin/campaign/*/import/check', {
    body: {
      status: 'success',
      data: {
        token: 'cypress-check-token-000000000000',
        checked_at: new Date(now).toISOString().replace(/\.\d+Z$/, 'Z'),
        expires_at: new Date(now + 3600 * 1000).toISOString().replace(/\.\d+Z$/, 'Z'),
        import_method: 'selected',
        source: { file_names: ['Example.jpg'] },
        columns: { name: null, file_id: null, ignored: [] },
        counts: {
          ok: 1, renamed: 0, duplicate: 0, unknown_name: 0,
          unknown_file_id: 0, malformed_file_id: 0, same_name: 0
        },
        blocking: false,
        total_rows: 1,
        importable_count: 1,
        issues: [],
        issues_total: 0,
        issues_truncated: false,
        same_name_groups: []
      }
    }
  }).as('checkImport')
}

const savedRound = () => ({
  id: 999,
  name: 'My Test Round',
  import: { new_round_entry_count: 1, warnings: [], disqualified: [] }
})


describe('Campaign Details Page', () => {
  beforeEach(() => {
    cy.setCookie('clastic_cookie', '<cookie-validation-string>');
    cy.visit('http://localhost:5173/#/')
    cy.get('div.coordinator-campaign-cards').find('.coordinator-campaign-card').first().click()
    cy.url().should('match', /\/campaign\/\d+/)
  })

  it('should display campaign title and rounds section', () => {
    cy.get('.campaign-title').should('be.visible')
    cy.get('.campaign-rounds').should('be.visible')
  })

  it('should enter edit mode and show editable fields', () => {
    cy.get('.campaign-button-group')
      .find('button')
      .contains('Edit campaign')
      .click()

    cy.get('.campaign-name-input').should('be.visible')
    cy.get('.date-time-inputs').should('be.visible')
  })

  it('should cancel edit mode', () => {
    cy.get('.campaign-button-group')
      .find('button')
      .contains('Edit campaign')
      .click()

    cy.get('.cancel-button').click()
    cy.get('.campaign-name-input').should('not.exist')
    cy.get('.campaign-title').should('be.visible')
  })

  it('should show new round form after clicking "Add Round"', () => {
    cy.get('.add-round-button').click()
    cy.get('.juror-campaign-round-card').should('be.visible')
    cy.get('.form-container').should('be.visible')
  })

  it('should enter campaign edit mode and show editable fields', () => {
    cy.get('[datatest="editbutton"]').click()
    cy.get('.campaign-name-input').should('be.visible')
    cy.get('.date-time-inputs').should('be.visible')
  })

   it('should save campaign edits', () => {
    cy.get('button').contains('Edit').first().click()
   cy.get('.campaign-name-input input').clear().type('Updated Campaign Name');
    cy.get('button').contains('Save').click()
    cy.contains('Updated Campaign Name').should('be.visible')
  })

  it('should cancel editing campaign details', () => {
    cy.get('[datatest="editbutton"]').click()
    cy.get('.cancel-button').click()
    cy.get('.campaign-name-input').should('not.exist')
    cy.get('.campaign-title').should('be.visible')
  })

  it('should not allow creating a new round when one is already active or paused', () => {
    cy.intercept('GET', '/v1/admin/campaign/*', {
      fixture: 'campaignWithActiveRound.json'
    }).as('getCampaign')

    cy.visit('/')
    cy.get('div.coordinator-campaign-cards').find('.coordinator-campaign-card').first().click()
    cy.wait('@getCampaign')

    cy.get('.add-round-button').click()
    cy.contains('Only one round can be maintained at a time').should('be.visible')
    cy.get('.juror-campaign-round-card').should('not.exist')
  })

 it('should create a new round successfully', () => {
  cy.get('.add-round-button').click()
  cy.get('.form-container input[type="text"]').first().clear().type('My Test Round')
  cy.get('.form-container').within(() => {
    cy.get('input[placeholder="YYYY-MM-DD"]').first().clear().type('2025-08-15')
  })
  cy.get('input[type="number"]').first().clear().type('3')
  cy.get('[data-testid="userlist-search"] input').type('AadarshM07');
  cy.get('[data-testid="userlist-search"]')
    .find('li')
    .first()
    .click();
  // #510 / #447: the source is checked first; Save sends the round together
  // with its checked import, once
  stubCheck()
  cy.intercept('POST', '/v1/admin/campaign/*/add_round', (req) => {
    req.reply({ delay: 500, body: { status: 'success', data: savedRound() } })
  }).as('addRound')
  cy.get('.form-container').contains('label', 'File List').click()
  cy.get('.form-container textarea').first().type('Example.jpg')
  cy.get('[data-testid="add-round-button"]').should('be.disabled')
  cy.get('[data-testid="check-source-button"]').click()
  cy.wait('@checkImport')
  cy.get('[data-testid="import-check-result"]').should('be.visible')
  // a double click must not save twice
  cy.get('[data-testid="add-round-button"]').click().click({ force: true })
  cy.wait('@addRound').its('request.body').should((body) => {
    expect(body.import).to.deep.equal({
      import_method: 'selected',
      check_token: 'cypress-check-token-000000000000'
    })
    expect(body).not.to.have.property('file_names')
  })
  cy.get('@addRound.all').should('have.length', 1)
  cy.get('.juror-campaign-round-card').should('not.exist')
})

it('keeps the form open when the server refuses the import', () => {
  cy.get('.add-round-button').click()
  cy.get('.form-container input[type="text"]').first().clear().type('My Test Round')
  cy.get('.form-container').within(() => {
    cy.get('input[placeholder="YYYY-MM-DD"]').first().clear().type('2025-08-15')
  })
  cy.get('[data-testid="userlist-search"] input').type('AadarshM07')
  cy.get('[data-testid="userlist-search"]').find('li').first().click()
  stubCheck()
  cy.intercept('POST', '/v1/admin/campaign/*/add_round', {
    statusCode: 400,
    body: { status: 'failure', error_type: 'import_check_expired', detail: 'check expired' }
  }).as('addRound')
  cy.get('.form-container').contains('label', 'File List').click()
  cy.get('.form-container textarea').first().type('Example.jpg')
  cy.get('[data-testid="check-source-button"]').click()
  cy.wait('@checkImport')
  cy.get('[data-testid="add-round-button"]').click()
  cy.wait('@addRound')
  cy.get('.juror-campaign-round-card').should('exist')
  cy.get('[data-testid="import-check-result"]').should('contain', 'expired')
  cy.get('[data-testid="add-round-button"]').should('be.disabled')
})


  it('should cancel round creation', () => {
    cy.get('.add-round-button').click()

    cy.get('.button-group')
      .find('button')
      .contains('Cancel')
      .click()

    cy.get('.juror-campaign-round-card').should('not.exist')
    cy.get('.add-round-button').should('be.visible')
  })

 

  it('should delete a round with confirmation', () => {
    cy.get('button').contains('Edit round').first().click()
    cy.get('button').contains('Delete').click()
    cy.get('.cdx-dialog')
      .find('button')
      .contains('Delete')
      .click()
    cy.wait(1000)
  })
})
