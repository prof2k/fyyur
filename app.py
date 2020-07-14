#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, abort, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
import sys
from datetime import datetime
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

migrate = Migrate(app, db)


#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(220))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))

    genres = db.Column(db.ARRAY(db.String))
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))
    shows = db.relationship('Show', backref="venue", lazy="joined")
 

class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.ARRAY(db.String))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))

    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))
    shows = db.relationship('Show', backref="artist", lazy="joined")

class Show(db.Model):
  __tablename__ = 'Show'

  id = db.Column(db.Integer, primary_key=True)
  artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable = False)
  venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable = False)
  start_time = db.Column(db.DateTime, nullable = False)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')

#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    locations = Venue.query.distinct(Venue.city, Venue.state).all()
    data = []
    for location in locations:
      venues_data = Venue.query.filter(Venue.city == location.city, Venue.state == location.state).all()  
      venue_data = []
      for venue in venues_data:
        venue_data.append({
          'id': venue.id,
          'name': venue.name,
          'num_upcoming_shows': Show.query.filter(Show.venue_id == venue.id).filter(Show.start_time > datetime.now()).count()
        })
      
      data.append({
        'city': location.city,
        'state': location.state,
        'venues': venue_data
      })
    return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  search_term = request.form.get('search_term', '')
  venues = Venue.query.filter(Venue.name.ilike(f'%{search_term}%')).all()
  count = len(venues)

  data = []
  for venue in venues:
    data.append({
      'id': venue.id,
      'name': venue.name
    })

  response = {
    'count': count,
    'data': data
  }

  return render_template('pages/search_venues.html', results=response, search_term=search_term)

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  venue = Venue.query.get(venue_id)
  if venue is None:
    abort(404)

  data = {
    "id": venue.id,
    "name": venue.name,
    "genres": venue.genres,
    "city": venue.city,
    "state": venue.state,
    "address": venue.address,
    "phone": venue.phone,
    "website": venue.website,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link
  }

  shows = Show.query.join(Artist, Artist.id == Show.artist_id).filter(Show.venue_id == venue_id).all()
  upcoming_shows = []
  past_shows = []

  for show in shows:
    if show.start_time > datetime.now():
      upcoming_shows.append({
        'artist_id': show.artist.id,
        'artist_name': show.artist.name,
        'artist_image_link': show.artist.image_link,
        'start_time': show.start_time.strftime("%Y-%m-%d, %H:%M:%S")
      })
      
    else:
      past_shows.append({
        'artist_id': show.artist.id,
        'artist_name': show.artist.name,
        'artist_image_link': show.artist.image_link,
        'start_time': show.start_time.strftime("%Y-%m-%d, %H:%M:%S")
      })

    upcoming_shows_count = len(upcoming_shows)
    past_shows_count = len(past_shows)

    data['upcoming_shows'] = upcoming_shows
    data['past_shows'] = past_shows
    data['upcoming_shows_count'] = upcoming_shows_count
    data['past_shows_count'] = past_shows_count

  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():  
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  error = False
  req = request.form
  try:
    name = req.get('name')
    city = req.get('city')
    state = req.get('state')
    address = req.get('address')
    phone = req.get('phone')
    image_link = req.get('image_link')
    facebook_link = req.get('facebook_link')
    genres = req.getlist('genres')#.slice(1, -1).split(',')
    website = req.get('website')
    seeking_talent = True if req.get('seeking_talent') == 'True' else False
    seeking_description = req.get('seeking_description')

    newVenue = Venue(
      name = name,
      city = city,
      state = state,
      address = address,
      phone = phone,
      image_link = image_link,
      facebook_link = facebook_link,
      genres = genres,
      website = website,
      seeking_talent = seeking_talent,
      seeking_description = seeking_description
    )

    db.session.add(newVenue)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  if error:
    flash('An error occurred. Venue ' + req.get('name') + ' could not be listed.')
    abort(500)  
  else:
    flash('Venue ' + req.get('name') + ' was successfully listed!')
    return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  error = False
  try:
    Venue.query.get(venue_id).delete()
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally: 
    db.session.close()
  if error:
    abort(500)
  else:
    redirect(url_for('index'))

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():

  data = Artist.query.all()
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  search_term = request.form.get('search_term', '')
  artists = Artist.query.filter(Artist.name.ilike(f'%{search_term}%')).all()
  count = len(artists)

  data = []
  for artist in artists:
    data.append({
      'id': artist.id,
      'name': artist.name
    })

  response = {
    'count': count,
    'data': data
  }
  return render_template('pages/search_artists.html', results=response, search_term=search_term)

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  artist = Artist.query.get(artist_id)
  if artist is None:
    abort(404)

  data = {
    "id": artist.id,
    "name": artist.name,
    "genres": artist.genres,
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link
  }

  shows = Show.query.join(Venue, Venue.id == Show.venue_id).filter(Show.artist_id == artist_id).all()
  upcoming_shows = []
  past_shows = []

  for show in shows:
    if show.start_time > datetime.now():
      upcoming_shows.append({
        'venue_id': show.venue.id,
        'venue_name': show.venue.name,
        'venue_image_link': show.venue.image_link,
        'start_time': show.start_time.strftime("%Y-%m-%d, %H:%M:%S")
      })
    else:
      past_shows.append({
        'venue_id': show.venue.id,
        'venue_name': show.venue.name,
        'venue_image_link': show.venue.image_link,
        'start_time': show.start_time.strftime("%Y-%m-%d, %H:%M:%S")
      })

    upcoming_shows_count = len(upcoming_shows)
    past_shows_count = len(past_shows)

    data['upcoming_shows'] = upcoming_shows
    data['past_shows'] = past_shows
    data['upcoming_shows_count'] = upcoming_shows_count
    data['past_shows_count'] = past_shows_count

  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  artist = Artist.query.get(artist_id)
  if artist:
    data = {
      "id" :  artist.id,
      "name" : artist.name,
      "genres" : artist.genres,
      "city" : artist.city,
      "state" : artist.state,
      "phone" : artist.phone,
      "website" : artist.website,
      "facebook_link" : artist.facebook_link,
      "seeking_venue" : artist.seeking_venue,
      "seeking_description" : artist.seeking_description,
      "image_link" : artist.image_link
    }
    form = ArtistForm(data = data)
  else:
    abort(404)

  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  artist = Artist.query.get(artist_id)
  
  error = False
  req = request.form
  try:
    artist.name = req.get('name')
    artist.city = req.get('city')
    artist.state = req.get('state')
    artist.phone = req.get('phone')
    artist.genres = req.getlist('genres')
    artist.image_link = req.get('image_link')
    artist.facebook_link = req.get('facebook_link')
    artist.website = req.get('website')
    artist.seeking_venue = True if req.get('seeking_venue') == 'True' else False
    artist.seeking_description = req.get('seeking_description')

    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info()) 
  finally:
    db.session.close()
  if error:
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be updated.')
    abort(500)
  else:
    flash('Artist ' + request.form['name'] + ' was successfully updated!')
    return redirect(url_for('show_artist', artist_id=artist_id))

  
@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  venue = Venue.query.get(venue_id)
  if venue:
    data = {
      "id" : venue.id,
      "name" : venue.name,
      "genres" : venue.genres,
      "city" : venue.city,
      "state" : venue.state,
      "address" : venue.address,
      "phone" : venue.phone,
      "website" : venue.website,
      "facebook_link" : venue.facebook_link,
      "seeking_talent" : venue.seeking_talent,
      "seeking_description" : venue.seeking_description,
      "image_link" : venue.image_link
    }
    form = VenueForm(data = data)
  else:
    abort(404)

  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  venue = Venue.query.get(venue_id)

  error = False
  req = request.form
  try:
    venue.name = req.get('name')
    venue.city = req.get('city')
    venue.state = req.get('state')
    venue.address = req.get('address')
    venue.phone = req.get('phone')
    venue.image_link = req.get('image_link')
    venue.facebook_link = req.get('facebook_link')
    venue.genres = req.getlist('genres')
    venue.website = req.get('website')
    venue.seeking_talent = True if req.get('seeking_talent') == 'True' else False
    venue.seeking_description = req.get('seeking_description')

    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  
  if error:
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be updated.')
    abort(500)
  else:
    flash('Venue ' + request.form['name'] + ' was successfully updated!')
    return redirect(url_for('show_venue', venue_id=venue_id))

  

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  error = False
  req = request.form
  try:
    name = req.get('name')
    city = req.get('city')
    state = req.get('state')
    phone = req.get('phone')
    genres = req.getlist('genres')
    image_link = req.get('image_link')
    facebook_link = req.get('facebook_link')
    website = req.get('website')
    seeking_venue = True if req.get('seeking_venue') == 'True' else False
    seeking_description = req.get('seeking_description')

    new_venue = Artist(
      name = name,
      city = city,
      state = state,
      genres = genres,
      phone = phone,
      image_link = image_link,
      facebook_link = facebook_link,
      website = website,
      seeking_venue = seeking_venue,
      seeking_description = seeking_description
    )

    db.session.add(new_venue)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  if error:
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
    abort(500)
  else:
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
    return render_template('pages/home.html')

#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  all_shows = Show.query.join(Artist, Artist.id == Show.artist_id).join(Venue, Venue.id == Show.venue_id).all()
  data = []
  for show in all_shows:
    if datetime.now() > show.start_time:
      continue
    data.append({
      "venue_id": show.venue_id,
      "venue_name": show.venue.name,
      "artist_id": show.artist_id,
      "artist_name": show.artist.name,
      "artist_image_link": show.artist.image_link,
      "start_time": show.start_time.strftime("%Y-%m-%d, %H:%M:%S")
    })
  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  error = False
  try:
    rf = request.form
    artist_id = rf['artist_id']
    venue_id = rf['venue_id']
    start_time = rf['start_time']

    new_show = Show(
      artist_id = artist_id,
      venue_id = venue_id,
      start_time = start_time
    )

    db.session.add(new_show)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  if error:
    flash('An error occurred. Show could not be listed')
    abort(500)
  else:
    flash('Show was successfully listed!')
    return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
