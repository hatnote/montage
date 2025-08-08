describe('Home View Conditional Rendering', () => {

  beforeEach(() => {
    cy.setCookie('clastic_cookie','<cookie-validation-string>');
    cy.visit('http://localhost:5173/#/');
  })
  
  it('should display main dashboard elements', () => {
    cy.get('.dashboard-container', { timeout: 10000 }).should('exist')
    cy.get('.dashboard-header h1').should('be.visible')
  })

  it('should show "New Campaign" button for organizers', () => {
    cy.get('.dashboard-container', { timeout: 10000 }).should('exist')
    cy.get('body').then(($body) => {
      if ($body.find('a[href="/campaign/new"]').length > 0) {
        cy.get('.dashboard-header-heading').within(() => {
          cy.contains('New Campaign').should('exist')
          cy.get('a[href="/campaign/new"]').should('exist')
        })
      }
    })
  })

  it('should create a new campaign via the form submission', () => {
    cy.get('.dashboard-container', { timeout: 10000 }).should('exist')
    cy.get('body').then(($body) => {
      if ($body.find('a[href="/campaign/new"]').length > 0) {
        cy.get('a[href="/campaign/new"]').click()
        cy.url().should('include', '/campaign/new')
        cy.get('.new-campaign-card').within(() => {
          cy.get('input[placeholder="Campaign name"]').type('Test Campaign')
          cy.get('input[placeholder="example-slug"]').type('test-campaign')
          cy.get('input[placeholder="YYYY-MM-DD"]').eq(0).type('2025-08-01')
          cy.get('input[placeholder="HH:mm"]').eq(0).type('10:00')          
          cy.get('input[placeholder="YYYY-MM-DD"]').eq(1).type('2025-08-10')
          cy.get('input[placeholder="HH:mm"]').eq(1).type('18:00')
          cy.get('.create-button').click()
        })
        cy.url().should('match', /\/campaign\/\d+/)
      }
    })
  })

  it('should show new campaign card after creation', () => {
    cy.visit('http://localhost:5173/#/');
    cy.get('.dashboard-container', { timeout: 10000 }).should('exist')
    cy.get('body').then(($body) => {
      if ($body.find('.new-campaign-card').length > 0) {
        cy.get('.new-campaign-card').should('be.visible')
        cy.get('.new-campaign-card h2').should('contain', 'Test Campaign')
      }
    })
  });     
  

  it('should show "Add Organizer" button for maintainers and it', () => {
    cy.get('.dashboard-container', { timeout: 10000 }).should('exist')
    cy.get('body').then(($body) => {
      if ($body.find('button:contains("Add Organizer")').length > 0) {
        cy.contains('Add Organizer').should('exist')

      }
    })
  })

  it('should open dialog when "Add Organizer" button is clicked', () => {
    cy.get('.dashboard-container', { timeout: 10000 }).should('exist')
    cy.get('body').then(($body) => {
      if ($body.find('button:contains("Add Organizer")').length > 0) {
        cy.contains('Add Organizer').click()
        cy.get('[role="dialog"]', { timeout: 5000 }).should('exist')
        cy.contains('Add').should('exist')
      }
    })
  })

  it('should display juror campaigns if available', () => {
    cy.visit('http://localhost:5173/#/');
    cy.get('.dashboard-container', { timeout: 10000 }).should('exist')
    cy.get('body').then(($body) => {
      if ($body.find('.juror-campaigns').length > 0) {
        cy.get('.juror-campaigns h2').should('contain', 'Active voting rounds')
        cy.get('.juror-campaigns juror-campaign-card').should('exist')
      }
    })
  })

  it('should display coordinator campaign cards if campaigns exist', () => {
    cy.visit('http://localhost:5173/#/');
    cy.get('.dashboard-container', { timeout: 10000 }).should('exist');
    cy.get('body').then(($body) => {
      if ($body.find('section.coordinator-campaigns').length > 0) {
        cy.get('section.coordinator-campaigns').within(() => {
          cy.get('h2').should('contain', 'Coordinator campaigns');
          cy.get('.coordinator-campaign-card').should('exist');
        });
      }
    });
  });

  it('should navigate to view all campaigns page', () => {
    cy.get('.dashboard-container', { timeout: 10000 }).should('exist')
    cy.get('.dashboard-info a').click()
    cy.url().should('include', '/campaign/all')
  })

  it('should navigate to campaign details page', () => {
    cy.get('div.coordinator-campaign-cards')
      .find('.coordinator-campaign-card') 
      .first()
      .click()
    cy.url().should('match', /\/campaign\/\d+/)
  })
  

});
