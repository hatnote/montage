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
    cy.get('.button-group button').contains('Add Round').click().click();
    cy.log(' Round created successfully');
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
