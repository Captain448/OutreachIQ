import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { Router, provideRouter } from '@angular/router';
import { LoginComponent } from './login.component';
import { AuthService } from '../../../core/services/auth.service';

describe('LoginComponent', () => {
  let component: LoginComponent;
  let fixture: ComponentFixture<LoginComponent>;
  let authServiceSpy: any;
  let router: Router;

  beforeEach(async () => {
    authServiceSpy = {
      login: () => of({ access_token: 'fake-jwt', token_type: 'bearer' })
    };

    await TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: authServiceSpy }
      ]
    }).compileComponents();

    router = TestBed.inject(Router);
    vi.spyOn(router, 'navigate').mockImplementation(() => Promise.resolve(true));

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should initialize with password hidden and submit button labeled Login', () => {
    expect(component.showPassword).toBe(false);
    expect(component.loading).toBe(false);

    const passwordInput: HTMLInputElement = fixture.nativeElement.querySelector('#password');
    expect(passwordInput.type).toBe('password');

    const submitBtn: HTMLButtonElement = fixture.nativeElement.querySelector('.btn-submit');
    expect(submitBtn.textContent?.trim()).toBe('Login');
  });

  it('should toggle password visibility when eye toggle button is clicked', () => {
    const eyeBtn: HTMLButtonElement = fixture.nativeElement.querySelector('.eye-toggle-btn');
    expect(eyeBtn).toBeTruthy();

    // Click to show password
    eyeBtn.click();
    fixture.detectChanges();

    expect(component.showPassword).toBe(true);
    const passwordInput: HTMLInputElement = fixture.nativeElement.querySelector('#password');
    expect(passwordInput.type).toBe('text');

    // Click to hide password
    eyeBtn.click();
    fixture.detectChanges();

    expect(component.showPassword).toBe(false);
    expect(passwordInput.type).toBe('password');
  });

  it('should maintain Login text on submit button during and after authentication', () => {
    const submitBtn: HTMLButtonElement = fixture.nativeElement.querySelector('.btn-submit');
    expect(submitBtn.textContent?.trim()).toBe('Login');

    component.form.setValue({
      email: 'test@example.com',
      password: 'password123'
    });
    fixture.detectChanges();

    // Trigger submit
    component.onSubmit();
    fixture.detectChanges();

    // Button should still say Login, not Authenticating...
    expect(submitBtn.textContent?.trim()).toBe('Login');
  });

  it('should display incorrect credentials error banner on HTTP 401 error', () => {
    authServiceSpy.login = () => throwError(() => ({
      status: 401,
      error: { detail: 'Incorrect email or password' }
    }));

    component.form.setValue({
      email: 'wrong@example.com',
      password: 'wrongpassword'
    });

    component.onSubmit();
    fixture.detectChanges();

    expect(component.loading).toBe(false);
    expect(component.errorMessage).toBe('Incorrect email or password. Please check your credentials and try again.');

    const errorBanner = fixture.nativeElement.querySelector('.error-banner');
    expect(errorBanner).toBeTruthy();
    expect(errorBanner.textContent?.trim()).toBe('Incorrect email or password. Please check your credentials and try again.');
  });

  it('should navigate to dashboard on successful login', () => {
    authServiceSpy.login = () => of({ access_token: 'valid-token', token_type: 'bearer' });

    component.form.setValue({
      email: 'user@domain.com',
      password: 'validpassword'
    });

    component.onSubmit();
    fixture.detectChanges();

    expect(component.loading).toBe(false);
    expect(component.errorMessage).toBe('');
    expect(router.navigate).toHaveBeenCalledWith(['/dashboard']);
  });
});
