import React from 'react';
import Immutable from 'immutable';

import RoundImagesInfo from './imagesinfo';

const Round = React.createClass({
    getInitialState() {
        // Can't use the Immutable Map directly, since React requires
        // state to be a plain JS object
        return {
            round: Immutable.Map({
                name: 'Some name',
                type: 'bool',
                state: 'draft', // Options are: draft, active, paused, completed
                judgingOptions: {
                    requiredJudgingsCount: 1
                },
                jury: ['UserA', 'UserB', 'UserC'],
                images: {},
                admins: ['UserX', 'UserY'],
            })
        };
    },
    handleChange(event) {
        let round = this.state.round;
        switch (event.target.name) {
            case "jury":
            case "admins":
                // For these two, state should be an array, separated by newlines.
                round = round.set(event.target.name, event.target.value.split('\n'))
                break;
            case 'requiredJudgingsCount':
                round = round.set('judgingOptions', {
                    requiredJudgingsCount: event.target.value
                })
                break;
            default:
                round = round.set(event.target.name, event.target.value);
        }
        this.setState({round: round});
    },
    render() {
        const round = this.state.round;
        let judgingOptions = null;
        switch (round.get('type')) {
            case 'bool':
            case 'rating':
                judgingOptions = <div className='form-group'>
                    <label>Number of jurors who must rate each image</label>
                    <input 
                        className='form-control'
                        type='number'
                        name='requiredJudgingsCount'
                        value={round.get('judgingOptions').requiredJudgingsCount}
                        onChange={this.handleChange} />
                    </div>
        }
        
        let juryReadOnly = round.get('state') === 'draft' || round.get('state') === 'paused' ? undefined : true;
        return <form className="col-sm-6 col-sm-offset-3">
            <div className="form-group">
                <label>Name</label>
                <input 
                    className="form-control"
                    type="text"
                    name="name"
                    value={round.get('name')}
                    onChange={this.handleChange} />
            </div>
            <div className="form-group">
                <label>Type</label>
                <select name="type" 
                        className="form-control" 
                        value={round.get('type')}
                        onChange={this.handleChange}>
                    <option value="bool">Yes/No</option>
                    <option value="rating">Rating</option>
                    <option value="ranking">Ranking</option>
                </select>
            </div>
            {judgingOptions}
            <div className="form-group">
                <label>Images</label>
                <RoundImagesInfo 
                    onImportFromCommons={this.props.onImportFromCommons}
                />
            </div>
            <div className="form-group">
                <label>Jury Members</label>
                <textarea 
                    className='form-control'
                    name="jury"
                    value={round.get('jury').join('\n')}
                    rows={round.get('jury').length}
                    readOnly={juryReadOnly}
                    onChange={this.handleChange} />
            </div>
            <div className="form-group">
                <label>Admin Members</label>
                <textarea 
                    className='form-control'
                    name="admins"
                    value={round.get('admins').join('\n')}
                    rows={round.get('admins').length}
                    onChange={this.handleChange} />
            </div>
        </form>
    }
    
})

export default Round;
