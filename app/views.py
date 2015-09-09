from app import app, lm, db
from flask import render_template, request, redirect, url_for, session, g, flash
from flask.ext.login import login_user, logout_user, current_user, login_required
from .forms import ImportanceForm, LoginForm, UserEditForm, LaptopEditForm
from .models import User, Laptop
from .auth import authenticate
from .log import Logger
from pbkdf2 import crypt
import json

logger = Logger()
logger.setLevel(logger.info)
user_level = ['Standard user', 'Moderator', 'Admin', 'Project Lead']

@lm.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.before_request
def before_request():
    g.user = current_user

@app.route('/')
@app.route('/index')
def index():
    if 'budget' in session:
        return redirect(url_for('options'))
    return redirect(url_for('budget'))


@app.route('/budget', methods=['GET', 'POST'])
def budget():
    try:
        session['budget'] = request.form['budget']
    except KeyError:
        return render_template('budget.html', extra_css=['budget'])
    return redirect(url_for('options'))


@app.route('/options', methods=['GET', 'POST'])
def options():
    if 'budget' in session:
        form = ImportanceForm()
        if form.validate_on_submit():
            data = session['budget'] + "e, "
            for field in form:
                data += str(field.data) + "<br>"
            return data
        return render_template('options.html', form=form, budget=session['budget'], extra_css=[])
    return redirect(url_for('budget'))

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    logger.log('Current user:'+str(g.user))
    if g.user.is_authenticated():
        return redirect(url_for('laptops'))
    return redirect(url_for('login'))

@app.route('/admin/laptops')
@login_required
def laptops():
    laptops = Laptop.query.all()
    return render_template('laptops.html', laptops=laptops, user=g.user, extra_css=[])

@app.route('/admin/laptops/<id>')
@login_required
def laptop_view(id):
    laptop = Laptop.query.filter_by(id=id).first()
    spec_list = json.loads(laptop.specs)
    data = ''
    for k in spec_list:
        data += '%s: %s<br>' % (k, spec_list[k])
    return data

@app.route('/admin/laptops/<id>/edit', methods=['GET', 'POST'])
@login_required
def laptop_edit(id):
    form = LaptopEditForm(prefix='laptop-form-')
    laptop = Laptop.query.filter_by(id=id).first()

    if form.validate_on_submit():
        spec_list = {
        'cpuBrand': form.cpuBrand.data,
        'cpuModel': form.cpuModel.data,
        'ram': form.ram.data,
        'gpuBrand': form.gpuBrand.data,
        'gpuModel': form.gpuModel.data,
        'ssd': form.ssd.data,
        'hdd': form.hdd.data,
        'odd': form.odd.data,
        'screenW': form.screenW.data,
        'screenH': form.screenH.data,
        'touch': form.touch.data,
        'batteryWh': form.batteryWh.data,
        'batteryTime': form.batteryTime.data,
        'width': form.width.data,
        'length': form.length.data,
        'thickness': form.thickness.data,
        'weight': form.weight.data
        }
        specs = json.dumps(spec_list)
        laptop.specs = specs
        laptop.brand = form.brand.data
        laptop.model = form.model.data
        laptop.size = form.size.data
        laptop.price = form.price.data
        db.session.add(laptop)
        db.session.commit()
        flash('msg_type_success')
        flash('Laptop updated succesfully!')
        return redirect(url_for('laptops'))
    spec_list = json.loads(laptop.specs)
    spec_list['brand']=laptop.brand
    spec_list['model']=laptop.model
    spec_list['size']=laptop.size
    spec_list['price']=laptop.price
    print spec_list['touch']
    return render_template('laptop_edit.html', user=g.user, form=form, spec_list=spec_list,  extra_css=[])


@app.route('/admin/laptops/add', methods=['GET', 'POST'])
@login_required
def laptop_add():
    form = LaptopEditForm(prefix='laptop-form-')
    if form.validate_on_submit():
        spec_list = {
        'cpuBrand': form.cpuBrand.data,
        'cpuModel': form.cpuModel.data,
        'ram': form.ram.data,
        'gpuBrand': form.gpuBrand.data,
        'gpuModel': form.gpuModel.data,
        'ssd': form.ssd.data,
        'hdd': form.hdd.data,
        'odd': form.odd.data,
        'screenW': form.screenW.data,
        'screenH': form.screenH.data,
        'touch': form.touch.data,
        'batteryWh': form.batteryWh.data,
        'batteryTime': form.batteryTime.data,
        'width': form.width.data,
        'length': form.length.data,
        'thickness': form.thickness.data,
        'weight': form.weight.data
        }
        specs = json.dumps(spec_list)
        laptop = Laptop(brand=form.brand.data, model=form.model.data, specs=specs, size=form.size.data, price=form.price.data)
        db.session.add(laptop)
        db.session.commit()
        flash('msg_type_success')
        flash('Laptop added succesfully!')
        return redirect(url_for('laptops'))
    return render_template('laptop_add.html', user=g.user, form=form, extra_css=[])

@app.route('/admin/stats')
@login_required
def stats():
    return render_template('stats.html', user=g.user, extra_css=[])

@app.route('/admin/users')
@login_required
def users():
    users = User.query.all()
    return render_template('users.html', user=g.user, level=user_level, users=users, extra_css=[])

@app.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
def user_add():
    if g.user.permissions < 3:
        flash('msg_type_warning')
        flash('Insufficient permissions!')
        return redirect(url_for('users'))
    form = UserEditForm(prefix='add-form-')
    if form.validate_on_submit():
        if form.password.data:
            #Permission checks
            if form.permissions.data == 4 and g.user.permissions < 4:
                flash('msg_type_warning')
                flash('Insufficient permissions!')
                return redirect(url_for('users'))

            u =  User(username=form.user.data, pwhash=crypt(form.password.data), permissions=form.permissions.data)
            db.session.add(u)
            db.session.commit()
            flash('msg_type_success')
            flash('User added succesfully!')
            return redirect(url_for('users'))
        form.password.errors.append('Please enter a password.')
    return render_template('user_add.html', user=g.user, form=form, extra_css=[])

@app.route('/admin/users/<username>', methods=['GET', 'POST'])
@login_required
def user_edit(username):
    form = UserEditForm(username, prefix='edit-form-')
    e_user = User.query.filter_by(username=username).first()
    if e_user == None:
        flash('msg_type_warning')
        flash('User not found!')
        return redirect(url_for('users'))
    #Permission checks
    if e_user.username != g.user.username:

        if e_user.permissions == 4 and g.user.permissions < 4:
            print 'Tried to edit project lead, %d:%d' % (e_user.permissions, g.user.permissions)
            flash('msg_type_warning')
            flash('Insufficient permissions!')
            return redirect(url_for('users'))
        if g.user.permissions < 3:
            print 'Not high enough , %d:%d' % (e_user.permissions, g.user.permissions)
            flash('msg_type_warning')
            flash('Insufficient permissions!')
            return redirect(url_for('users'))

    if form.validate_on_submit():
        if form.remove.data:
            db.session.delete(e_user)
            db.session.commit()
            flash('msg_type_success')
            flash('User removed succesfully.')
            return redirect(url_for('users'))
        e_user.username=form.user.data
        if len(form.password.data) > 0:
            e_user.pwhash=crypt(form.password.data)
        if g.user.permissions == 4:
            e_user.permissions=form.permissions.data
        db.session.add(e_user)
        db.session.commit()
        flash('msg_type_success')
        flash('Your changes have been saved!')
        return redirect(url_for('users'))
    form.user.data = e_user.username
    return render_template('user_edit.html', user=g.user, editing=e_user, form=form, extra_css=['edit'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user is not None and g.user.is_authenticated():
        logger.log('Redirecting...')
        return redirect(url_for('admin'))
    form = LoginForm(prefix='login-form-')
    if form.validate_on_submit():
        logger.log('Form validation requested.')
        session['remember_me'] = form.remember_me.data
        remember_me = False
        if 'remember_me' in session:
            remember_me = session['remember_me']
            session.pop('remember_me', None)
        user = authenticate(form.user.data, form.password.data)
        if user:
            login_user(user, remember=remember_me)
            logger.log('Login succesful')
            logger.log('User: '+str(g.user))
            return redirect(url_for('laptops'))
        else:
            form.password.errors.append('Invalid credentials!')
            logger.log('Authentication failed')
            return render_template('login.html', form=form, extra_css=['login'])
    return render_template('login.html', form=form, extra_css=['login'])

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

'''@app.route('/post', methods=['GET', 'POST'])
def post():
	return request.form['budget']
'''
