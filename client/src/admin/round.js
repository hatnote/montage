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
                description: 'Some longish description goes here maybe?',
                type: 'bool',
                state: 'active', // Options are: draft, active, paused, completed
                quorum: 1,
                jury: ['UserA', 'UserB', 'UserC'],
                images: {},
            })
        };
    },
    handleChange(event) {
        let round = this.state.round;
        switch (event.target.name) {
            case "jury":
                round = round.set(event.target.name, event.target.value.split('\n'))
                break;
            default:
                round = round.set(event.target.name, event.target.value);
        }
        this.setState({round: round});
    },
    render() {
        const round = this.state.round;
        let quorumOptions;
        let roundStateActions;
        switch (round.get('type')) {
            case 'bool':
            case 'rating':
                quorumOptions = <div className='form-group'>
                    <label>Number of jurors who must rate each image</label>
                    <input 
                        className='form-control'
                        type='number'
                        name='quorum'
                        value={round.get('quorum')}
                        onChange={this.handleChange} />
                    </div>
                break;
            default:
                quorumOptions = null; // Do not display it!
        }
        
        switch (round.get('state')) {
            case 'draft':
            case 'paused':
                roundStateActions = <button
                                        onClick={this.props.onActivateRound}
                                        className='btn'>Activate Round</button>
                break;
            case 'active':
                roundStateActions = [
                    <button
                        className='btn btn-warning'
                        onClick={this.handleAction}>Pause round</button>,
                    <button
                        className='btn btn-success'
                        onClick={this.handleAction}>Complete round</button>
                ]
                break;
            default:
                roundStateActions = null;
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
                <label>Description</label>
                <textarea
                    className='form-control'
                    name="jury"
                    value={round.get('description')}
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
            {quorumOptions}
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
            <div className='form-group col-sm-8'>
                <div className="btn-group">
                    {roundStateActions}
                </div>
            </div>
            <div className='form-group  pull-right'>
                <button type="submit" className="btn btn-primary">Save</button>
            </div>
        </form>
    }
    
})

export default Round;
